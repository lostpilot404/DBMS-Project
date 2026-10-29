"""Role work queues and connected care operations; reuse v6 master/ledger tables."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from .api import (
    RESOURCES,
    ApiError,
    _cast_value,
    _check_doctor_slot,
    _db,
    _fetch_one,
    _fetch_rows,
    _field,
    _parse_integer,
    _request_json,
    _snapshot,
    _transaction,
    _validate_date,
    _validate_payload,
    hospital_today,
)
from .auth import (
    ROLES,
    STAFF_ROLES,
    audit,
    check_patient,
    insert,
    patient_scope,
    require,
)

work = Blueprint("work", __name__)


def ident(p, k):
    return _parse_integer(p.get(k), k, minimum=1, maximum=9999999999)


def text(p, k, limit, required=True):
    if not required and p.get(k) in (None, ""):
        return None
    return _cast_value(
        _field("string", max_length=limit, required=required, nullable=not required),
        p.get(k),
        k,
    )


def money(p, k):
    return _cast_value(_field("money", nullable=False), p.get(k, "0"), k)


def row(c, sql, binds):
    r = _fetch_one(c, sql, binds)
    if r is None:
        raise ApiError("Record not found.", 404, "not_found")
    return r


def encounter(c, eid, open_only=False):
    e = row(
        c,
        "SELECT encounter_id,patient_id,doctor_id,appointment_id,admission_id,status FROM HMS_Encounter WHERE encounter_id=:id",
        {"id": eid},
    )
    if g.user["role"] == "doctor" and int(e["doctor_id"]) != g.user["doctor_id"]:
        raise ApiError("Record not found.", 404, "not_found")
    check_patient(int(e["patient_id"]), c)
    if open_only and e["admission_id"] and g.user["role"] == "doctor":
        require_inpatient_assignment(c, e["patient_id"], e["doctor_id"])
    if open_only and e["status"] != "Open":
        raise ApiError(
            "Completed consultation is retained; start a new encounter for further care.",
            409,
            "encounter_closed",
        )
    return e


def require_inpatient_assignment(c, patient_id, doctor_id):
    c.execute(
        "SELECT COUNT(*) FROM HMS_Care_Assignment WHERE patient_id=:patient AND doctor_id=:doctor AND is_active='Y'",
        {"patient": patient_id, "doctor": doctor_id},
    )
    if not c.fetchone()[0]:
        raise ApiError(
            "Active inpatient care requires a manager doctor assignment.",
            403,
            "forbidden",
        )


def care_charge(c, eid, kind, sid, description, qty, price):
    if Decimal(str(price)) * qty > Decimal("99999999.99"):
        raise ApiError("Care charge exceeds supported line total.")
    insert(
        c,
        "HMS_Care_Charge",
        {
            "encounter_id": eid,
            "source_kind": kind,
            "source_id": sid,
            "description": description,
            "quantity": qty,
            "unit_price": price,
        },
        "charge_id",
    )


@work.get("/api/workspace")
def workspace():
    require(*ROLES)
    role = g.user["role"]
    u = g.user
    page = _parse_integer(
        request.args.get("page", "1"), "page", minimum=1, maximum=10000
    )
    size = 40
    offset = (page - 1) * size
    query = (request.args.get("q") or "").strip().upper()
    if len(query) > 100:
        raise ApiError("Search must be at most100 characters.")
    queues = {}
    counts = {}
    definitions = {}
    notifications = {}
    with _snapshot() as conn:
        with conn.cursor() as c:

            def queue(name, sql, binds=None, search=None):
                binds = dict(binds or {})
                if query and search:
                    sql = (
                        "SELECT * FROM ("
                        + sql
                        + ") w WHERE UPPER(w."
                        + search
                        + ") LIKE :search"
                    )
                    binds["search"] = "%" + query + "%"
                definitions[name] = (sql, binds.copy())
                c.execute("SELECT COUNT(*) FROM (" + sql + ") w", binds)
                counts[name] = int(c.fetchone()[0])
                c.execute(
                    "SELECT * FROM ("
                    + sql
                    + ") w ORDER BY 1 DESC OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY",
                    {**binds, "offset": offset, "limit": size},
                )
                queues[name] = _fetch_rows(c)

            if role in ("manager", "doctor", "patient", "nurse"):
                clause, b = patient_scope("e")
                where = "1=1" if role == "manager" else clause
                if role == "doctor":
                    where += " AND e.doctor_id=:self_doctor"
                    b["self_doctor"] = u["doctor_id"]
                if role == "patient":
                    where += " AND e.status='Completed'"
                queue(
                    "consultations",
                    "SELECT e.encounter_id,e.patient_id,p.patient_name,e.doctor_id,e.appointment_id,e.admission_id,e.diagnosis,e.clinical_notes,e.status,e.recorded_at FROM HMS_Encounter e JOIN Patient p ON p.patient_id=e.patient_id WHERE "
                    + where,
                    b,
                    "patient_name",
                )
            if role in (
                "manager",
                "doctor",
                "receptionist",
                "patient",
                "nurse",
                "cashier",
            ):
                clause, b = patient_scope("p")
                queue(
                    "patients",
                    "SELECT p.patient_id,p.patient_name"
                    + ("" if role == "cashier" else ",p.date_of_birth,p.gender")
                    + (",p.phone,p.address" if role == "patient" else "")
                    + " FROM Patient p WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
            if role in ("manager", "receptionist", "patient", "doctor"):
                clause, b = (
                    patient_scope("r") if role in ("doctor", "patient") else ("1=1", {})
                )
                if role == "doctor":
                    clause += " AND r.doctor_id=:rd"
                    b["rd"] = u["doctor_id"]
                queue(
                    "requests",
                    "SELECT r.request_id,r.patient_id,p.patient_name,r.doctor_id,r.requested_date,r.requested_time,r.reason,r.status,r.appointment_id FROM HMS_Appointment_Request r JOIN Patient p ON p.patient_id=r.patient_id WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
                clause, b = (
                    patient_scope("a")
                    if role == "patient"
                    else ("a.doctor_id=:rd", {"rd": u["doctor_id"]})
                    if role == "doctor"
                    else ("1=1", {})
                )
                queue(
                    "appointments",
                    "SELECT a.appointment_id,a.patient_id,p.patient_name,a.doctor_id,a.appointment_date,a.appointment_time,a.duration_minutes,a.status FROM Appointment a JOIN Patient p ON p.patient_id=a.patient_id WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
                queue(
                    "doctors",
                    "SELECT doctor_id,doctor_name,specialization FROM Doctor",
                    search="doctor_name",
                )
            if role in ("manager", "nurse", "doctor", "patient"):
                clause, b = patient_scope("a")
                queue(
                    "admissions",
                    "SELECT a.admission_id,a.patient_id,p.patient_name,a.room_id,r.room_number,a.admission_date,a.discharge_date FROM Admission a JOIN Patient p ON p.patient_id=a.patient_id JOIN Room r ON r.room_id=a.room_id WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
                clause, b = patient_scope("a")
                queue(
                    "observations",
                    "SELECT o.observation_id,o.admission_id,a.patient_id,p.patient_name,o.observation,o.recorded_at FROM HMS_Observation o JOIN Admission a ON a.admission_id=o.admission_id JOIN Patient p ON p.patient_id=a.patient_id WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
            if role in ("manager", "patient", "doctor", "pharmacist"):
                clause, b = (
                    patient_scope("rx")
                    if role in ("doctor", "patient")
                    else ("1=1", {})
                )
                queue(
                    "prescriptions",
                    "SELECT rx.prescription_id,rx.patient_id,p.patient_name,rx.encounter_id,rx.medicine_id,m.medicine_name,rx.dosage,rx.duration,rx.ordered_quantity,CASE WHEN EXISTS(SELECT 1 FROM HMS_Order_Cancel x WHERE x.prescription_id=rx.prescription_id) THEN 'Cancelled' ELSE 'Active' END order_status,rx.prescription_date,NVL((SELECT SUM(d.quantity) FROM HMS_Dispense d WHERE d.prescription_id=rx.prescription_id),0) AS dispensed_quantity FROM Prescription rx JOIN Patient p ON p.patient_id=rx.patient_id JOIN Medicine m ON m.medicine_id=rx.medicine_id WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
                clause, b = (
                    patient_scope("rx")
                    if role in ("doctor", "patient")
                    else ("1=1", {})
                )
                queue(
                    "dispensing",
                    "SELECT d.dispense_id,rx.patient_id,p.patient_name,d.prescription_id,d.batch_id,d.quantity,d.recorded_at FROM HMS_Dispense d JOIN Prescription rx ON rx.prescription_id=d.prescription_id JOIN Patient p ON p.patient_id=rx.patient_id WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
            if role in ("manager", "doctor", "pharmacist"):
                queue(
                    "medicines",
                    "SELECT medicine_id,medicine_name,price,stock_quantity FROM Medicine",
                    search="medicine_name",
                )
            if role in ("manager", "pharmacist"):
                queue(
                    "batches",
                    "SELECT b.batch_id,b.medicine_id,m.medicine_name,b.batch_number,b.expires_on,b.quantity,CASE WHEN b.expires_on<HMS_Today() THEN 'Expired' WHEN b.expires_on<=HMS_Today()+30 THEN 'Expiring soon' ELSE 'In date' END AS expiry_alert FROM HMS_Medicine_Batch b JOIN Medicine m ON m.medicine_id=b.medicine_id",
                    search="medicine_name",
                )
                queue(
                    "low_stock",
                    "SELECT medicine_id,medicine_name,stock_quantity FROM Medicine WHERE stock_quantity<10",
                    search="medicine_name",
                )
            if role in ("manager", "doctor", "lab", "patient"):
                clause, b = (
                    patient_scope("e") if role in ("doctor", "patient") else ("1=1", {})
                )
                if role == "patient":
                    clause += " AND t.status='Resulted' AND e.status='Completed'"
                # Lab gets minimum order identity, not clinical notes/diagnoses.
                queue(
                    "tests",
                    "SELECT t.order_id,t.encounter_id,e.patient_id,p.patient_name,tc.test_name,CASE WHEN EXISTS(SELECT 1 FROM HMS_Order_Cancel x WHERE x.order_id=t.order_id) THEN 'Cancelled' ELSE t.status END status,r.result_id,r.result_text,r.recorded_at FROM HMS_Test_Order t JOIN HMS_Encounter e ON e.encounter_id=t.encounter_id JOIN Patient p ON p.patient_id=e.patient_id JOIN HMS_Test_Catalog tc ON tc.test_id=t.test_id LEFT JOIN HMS_Test_Result r ON r.order_id=t.order_id WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
            if role in ("manager", "doctor"):
                queue(
                    "test_catalog",
                    "SELECT test_id,test_name,fee,is_active FROM HMS_Test_Catalog WHERE is_active='Y'",
                    search="test_name",
                )
            if role in ("manager", "cashier", "patient"):
                clause, b = patient_scope("b") if role == "patient" else ("1=1", {})
                queue(
                    "bills",
                    "SELECT b.bill_id,b.patient_id,p.patient_name,b.bill_date,b.billed,b.paid,b.balance,b.ledger_status FROM V_Invoice_Balances b JOIN Patient p ON p.patient_id=b.patient_id WHERE "
                    + clause,
                    b,
                    "patient_name",
                )
            if role in ("manager", "cashier"):
                queue(
                    "return_review",
                    "SELECT event_id,bill_id,patient_id,dispense_id,quantity,unit_price,eligible_credit,credited,remaining_credit FROM V_HMS_Return_Review WHERE remaining_credit>0",
                )
            if role in ("manager", "cashier", "patient"):
                clause, b = patient_scope("b") if role == "patient" else ("1=1", {})
                queue(
                    "payments",
                    "SELECT pay.payment_id,pay.bill_id,b.patient_id,pay.amount,pay.payment_method,pay.reference,pay.recorded_at,pay.recorded_timezone FROM Bill_Payment pay JOIN Bill b ON b.bill_id=pay.bill_id WHERE "
                    + clause,
                    b,
                )
            if role in ("manager", "cashier"):
                queue(
                    "billing_admissions",
                    "SELECT a.admission_id,a.patient_id,p.patient_name,a.discharge_date FROM Admission a JOIN Patient p ON p.patient_id=a.patient_id",
                    search="patient_name",
                )
                queue(
                    "billing_encounters",
                    "SELECT e.encounter_id,e.patient_id,p.patient_name,e.status FROM HMS_Encounter e JOIN Patient p ON p.patient_id=e.patient_id",
                    search="patient_name",
                )
                queue(
                    "unbilled_charges",
                    "SELECT ch.charge_id,ch.encounter_id,e.patient_id,p.patient_name,e.admission_id,ch.source_kind,ch.description,ch.quantity,ch.unit_price FROM V_HMS_Care_Net ch JOIN HMS_Encounter e ON e.encounter_id=ch.encounter_id JOIN Patient p ON p.patient_id=e.patient_id WHERE ch.bill_item_id IS NULL AND ch.quantity>0",
                    search="patient_name",
                )
            if role in ("manager", "nurse", "maintenance", "receptionist"):
                queue(
                    "rooms",
                    "SELECT room_id,room_number,room_type,availability_status FROM Room",
                    search="room_number",
                )
            if role in ("manager", "maintenance"):
                queue(
                    "maintenance",
                    "SELECT t.task_id,t.room_id,r.room_number,t.description,t.status FROM HMS_Maintenance_Task t JOIN Room r ON r.room_id=t.room_id",
                    search="description",
                )
            if role == "manager":
                queue(
                    "staff",
                    "SELECT staff_id,full_name,staff_kind,is_active FROM HMS_Staff",
                    search="full_name",
                )
                queue(
                    "care_assignments",
                    "SELECT assignment_id,patient_id,doctor_id,is_active FROM HMS_Care_Assignment",
                )
                queue(
                    "ward_assignments",
                    "SELECT assignment_id,admission_id,user_id,is_active FROM HMS_Ward_Assignment",
                )
                queue(
                    "audit",
                    "SELECT audit_id,user_id,action,entity,record_id,recorded_at FROM HMS_Audit",
                )
                queue(
                    "settings",
                    "SELECT hospital_timezone,consultation_fee,multiuser_version FROM HMS_Settings",
                )
            pending_rules = {
                "requests": "status='Pending'",
                "tests": "status='Ordered'",
                "bills": "balance>0",
                "maintenance": "status IN ('Open','InProgress')",
                "low_stock": "1=1",
                "batches": "quantity>0 AND expiry_alert IN ('Expired','Expiring soon')",
                "prescriptions": "ordered_quantity>dispensed_quantity AND order_status='Active'",
            }
            for name, condition in pending_rules.items():
                if name in definitions:
                    sql, b = definitions[name]
                    c.execute(
                        "SELECT COUNT(*) FROM (" + sql + ") w WHERE " + condition, b
                    )
                    notifications[name] = int(c.fetchone()[0])
    return jsonify(
        {
            "data": {
                "role": role,
                "queues": queues,
                "counts": counts,
                "page": page,
                "page_size": size,
                "notifications": notifications,
            }
        }
    )


ACTIONS = {
    "staff": ("manager",),
    "update_staff": ("manager",),
    "assign_doctor": ("manager",),
    "assign_ward": ("manager",),
    "settings": ("manager",),
    "test_catalog": ("manager",),
    "update_test_catalog": ("manager",),
    "request_appointment": ("patient", "doctor", "manager"),
    "review_request": ("manager", "receptionist"),
    "consultation": ("doctor", "manager"),
    "complete_consultation": ("doctor", "manager"),
    "prescribe": ("doctor", "manager"),
    "order_test": ("doctor", "manager"),
    "observation": ("nurse", "manager"),
    "result": ("lab", "manager"),
    "receive_batch": ("pharmacist", "manager"),
    "dispense": ("pharmacist", "manager"),
    "prepare_bill": ("cashier", "manager"),
    "maintenance_request": ("manager", "nurse", "receptionist"),
    "maintenance_start": ("maintenance", "manager"),
    "maintenance_complete": ("maintenance", "manager"),
}


@work.post("/api/work/<action>")
def perform(action):
    if action not in ACTIONS:
        raise ApiError("Unknown workflow.", 404, "not_found")
    require(*ACTIONS[action])
    p = _request_json()
    uid = g.user["user_id"]
    result = None
    with _transaction(_db()) as conn:
        with conn.cursor() as c:
            receipt_key = None
            if action == "receive_batch" and "idempotency_key" not in p:
                raise ApiError("Batch receipts require a durable UUID idempotency_key.")
            if action == "receive_batch" and "idempotency_key" in p:
                import hashlib
                import json
                import uuid

                try:
                    receipt_key = str(uuid.UUID(str(p["idempotency_key"])))
                except (ValueError, TypeError, AttributeError):
                    raise ApiError("Supply a UUID idempotency_key.") from None
                receipt_hash = hashlib.sha256(
                    json.dumps(
                        {k: v for k, v in p.items() if k != "idempotency_key"},
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
                c.execute(
                    "SELECT user_id,action,payload_hash,result_id FROM HMS_Operation WHERE operation_key=:key",
                    {"key": receipt_key},
                )
                old = c.fetchone()
                if old:
                    if (int(old[0]), old[1], old[2]) != (uid, action, receipt_hash):
                        raise ApiError(
                            "Receipt key belongs to different details or actor.",
                            409,
                            "idempotency_mismatch",
                        )
                    return jsonify(data={"id": int(old[3]), "replayed": True}), 200
            if action == "staff":
                kind = p.get("staff_kind")
                if kind not in STAFF_ROLES:
                    raise ApiError("Choose a staff role.")
                result = insert(
                    c,
                    "HMS_Staff",
                    {
                        "full_name": text(p, "full_name", 150),
                        "staff_kind": kind,
                        "phone": text(p, "phone", 20, False),
                    },
                    "staff_id",
                )
            elif action == "update_staff":
                sid = ident(p, "staff_id")
                staff = row(
                    c,
                    "SELECT staff_id,is_active FROM HMS_Staff WHERE staff_id=:id",
                    {"id": sid},
                )
                changes = {}
                if "full_name" in p:
                    changes["full_name"] = text(p, "full_name", 150)
                if "phone" in p:
                    changes["phone"] = text(p, "phone", 20, False)
                if "is_active" in p:
                    if p["is_active"] not in ("Y", "N"):
                        raise ApiError("is_active must be Y or N.")
                    changes["is_active"] = p["is_active"]
                    if p["is_active"] == "N" and staff["is_active"] == "Y":
                        c.execute(
                            "SELECT COUNT(*) FROM HMS_User WHERE staff_id=:id AND role='manager' AND is_active='Y'",
                            {"id": sid},
                        )
                        if c.fetchone()[0]:
                            c.execute(
                                "SELECT COUNT(*) FROM HMS_User u JOIN HMS_Staff s ON s.staff_id=u.staff_id WHERE u.role='manager' AND u.is_active='Y' AND s.is_active='Y'"
                            )
                            if c.fetchone()[0] <= 1:
                                raise ApiError(
                                    "Cannot deactivate the last active manager.",
                                    409,
                                    "last_manager",
                                )
                if not changes:
                    raise ApiError("Provide staff fields to change.")
                c.execute(
                    "UPDATE HMS_Staff SET "
                    + ",".join(k + "=:" + k for k in changes)
                    + " WHERE staff_id=:id",
                    {**changes, "id": sid},
                )
                c.execute(
                    "DELETE FROM HMS_Session WHERE user_id IN (SELECT user_id FROM HMS_User WHERE staff_id=:id)",
                    {"id": sid},
                )
                result = sid
            elif action in ("assign_doctor", "assign_ward"):
                table = (
                    "HMS_Care_Assignment"
                    if action == "assign_doctor"
                    else "HMS_Ward_Assignment"
                )
                a, b = (
                    ("patient_id", "doctor_id")
                    if action == "assign_doctor"
                    else ("admission_id", "user_id")
                )
                vals = {
                    a: ident(p, a),
                    b: ident(p, b),
                    "is_active": p.get("is_active", "Y"),
                }
                if vals["is_active"] not in ("Y", "N"):
                    raise ApiError("is_active must be Y or N.")
                if action == "assign_ward":
                    target = row(
                        c,
                        "SELECT u.role FROM HMS_User u JOIN HMS_Staff s ON s.staff_id=u.staff_id WHERE u.user_id=:id AND u.is_active='Y' AND s.is_active='Y'",
                        {"id": vals[b]},
                    )
                    if target["role"] != "nurse":
                        raise ApiError("Ward assignee must be an active nurse.")
                    admission = row(
                        c,
                        "SELECT discharge_date FROM Admission WHERE admission_id=:id",
                        {"id": vals[a]},
                    )
                    if admission["discharge_date"] is not None:
                        raise ApiError("Cannot assign a discharged admission.")
                c.execute(
                    f"UPDATE {table} SET is_active=:is_active WHERE {a}=:{a} AND {b}=:{b}",
                    vals,
                )
                if c.rowcount == 0:
                    result = insert(c, table, vals, "assignment_id")
                else:
                    result = int(
                        row(
                            c,
                            f"SELECT assignment_id FROM {table} WHERE {a}=:{a} AND {b}=:{b}",
                            {a: vals[a], b: vals[b]},
                        )["assignment_id"]
                    )
            elif action == "settings":
                c.execute(
                    "UPDATE HMS_Settings SET consultation_fee=:fee WHERE singleton=1",
                    {"fee": money(p, "consultation_fee")},
                )
                result = 1
            elif action == "test_catalog":
                result = insert(
                    c,
                    "HMS_Test_Catalog",
                    {"test_name": text(p, "test_name", 150), "fee": money(p, "fee")},
                    "test_id",
                )
            elif action == "update_test_catalog":
                tid = ident(p, "test_id")
                row(
                    c,
                    "SELECT test_id FROM HMS_Test_Catalog WHERE test_id=:id",
                    {"id": tid},
                )
                changes = {}
                if "test_name" in p:
                    changes["test_name"] = text(p, "test_name", 150)
                if "fee" in p:
                    changes["fee"] = money(p, "fee")
                if "is_active" in p:
                    if p["is_active"] not in ("Y", "N"):
                        raise ApiError("is_active must be Y or N.")
                    changes["is_active"] = p["is_active"]
                if not changes:
                    raise ApiError("Provide catalogue fields to change.")
                c.execute(
                    "UPDATE HMS_Test_Catalog SET "
                    + ",".join(k + "=:" + k for k in changes)
                    + " WHERE test_id=:id",
                    {**changes, "id": tid},
                )
                result = tid
            elif action == "request_appointment":
                pid = (
                    g.user["patient_id"]
                    if g.user["role"] == "patient"
                    else ident(p, "patient_id")
                )
                check_patient(pid, c)
                eid = ident(p, "encounter_id") if p.get("encounter_id") else None
                if eid:
                    e = encounter(c, eid)
                    if int(e["patient_id"]) != pid:
                        raise ApiError("Follow-up patient mismatch.")
                day = _validate_date(p.get("requested_date"), "requested_date")
                if day.date() < hospital_today():
                    raise ApiError("Request a hospital date today or later.")
                clock = text(p, "requested_time", 5)
                if not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", clock):
                    raise ApiError("Use HH:MM.")
                did = (
                    g.user["doctor_id"]
                    if g.user["role"] == "doctor"
                    else ident(p, "doctor_id")
                )
                result = insert(
                    c,
                    "HMS_Appointment_Request",
                    {
                        "patient_id": pid,
                        "doctor_id": did,
                        "requested_date": day,
                        "requested_time": clock,
                        "reason": text(p, "reason", 300, False),
                        "encounter_id": eid,
                    },
                    "request_id",
                )
            elif action == "review_request":
                rid = ident(p, "request_id")
                r = row(
                    c,
                    "SELECT * FROM HMS_Appointment_Request WHERE request_id=:id",
                    {"id": rid},
                )
                if r["status"] != "Pending":
                    raise ApiError(
                        "Request has already been reviewed.", 409, "request_reviewed"
                    )
                decision = p.get("decision")
                if decision not in ("Accepted", "Rejected"):
                    raise ApiError("Choose Accepted or Rejected.")
                aid = None
                if decision == "Accepted":
                    vals = _validate_payload(
                        RESOURCES["appointments"],
                        {
                            "patient_id": r["patient_id"],
                            "doctor_id": r["doctor_id"],
                            "appointment_date": str(r["requested_date"])[:10],
                            "appointment_time": r["requested_time"],
                            "duration_minutes": p.get("duration_minutes", 30),
                        },
                        partial=False,
                    )
                    if vals["appointment_date"].date() < hospital_today():
                        raise ApiError("Request is now in the past.")
                    _check_doctor_slot(c, vals, None)
                    aid = insert(c, "Appointment", vals, "appointment_id")
                c.execute(
                    "UPDATE HMS_Appointment_Request SET status=:status,appointment_id=:aid WHERE request_id=:id",
                    {"status": decision, "aid": aid, "id": rid},
                )
                result = aid
            elif action == "consultation":
                pid = ident(p, "patient_id")
                check_patient(pid, c)
                did = (
                    g.user["doctor_id"]
                    if g.user["role"] == "doctor"
                    else ident(p, "doctor_id")
                )
                aid = ident(p, "appointment_id") if p.get("appointment_id") else None
                admission = ident(p, "admission_id") if p.get("admission_id") else None
                if bool(aid) == bool(admission):
                    raise ApiError(
                        "Choose exactly one appointment or active admission."
                    )
                if aid:
                    a = row(
                        c,
                        "SELECT patient_id,doctor_id,status FROM Appointment WHERE appointment_id=:id",
                        {"id": aid},
                    )
                    if (int(a["patient_id"]), int(a["doctor_id"])) != (pid, did):
                        raise ApiError(
                            "Appointment ownership mismatch.", 403, "forbidden"
                        )
                    if a["status"] != "Waiting":
                        raise ApiError(
                            "Reception must place the checked-in patient in Waiting.",
                            409,
                            "not_waiting",
                        )
                    c.execute(
                        "UPDATE Appointment SET status='In Consultation' WHERE appointment_id=:id",
                        {"id": aid},
                    )
                else:
                    if g.user["role"] == "doctor":
                        require_inpatient_assignment(c, pid, did)
                    a = row(
                        c,
                        "SELECT patient_id,discharge_date FROM Admission WHERE admission_id=:id",
                        {"id": admission},
                    )
                    if int(a["patient_id"]) != pid or a["discharge_date"] is not None:
                        raise ApiError("Active admission patient mismatch.")
                result = insert(
                    c,
                    "HMS_Encounter",
                    {
                        "patient_id": pid,
                        "doctor_id": did,
                        "appointment_id": aid,
                        "admission_id": admission,
                        "diagnosis": text(p, "diagnosis", 1000, False),
                        "clinical_notes": text(p, "clinical_notes", 2000, False),
                    },
                    "encounter_id",
                )
                c.execute("SELECT consultation_fee FROM HMS_Settings WHERE singleton=1")
                fee = Decimal(str(c.fetchone()[0]))
                care_charge(c, result, "Consultation", result, "Consultation", 1, fee)
            elif action == "complete_consultation":
                eid = ident(p, "encounter_id")
                e = encounter(c, eid, True)
                if e["appointment_id"]:
                    c.execute(
                        "UPDATE Appointment SET status='Completed' WHERE appointment_id=:id",
                        {"id": e["appointment_id"]},
                    )
                c.execute(
                    "UPDATE HMS_Encounter SET diagnosis=:diagnosis,clinical_notes=:notes,status='Completed' WHERE encounter_id=:id",
                    {
                        "diagnosis": text(p, "diagnosis", 1000),
                        "notes": text(p, "clinical_notes", 2000),
                        "id": eid,
                    },
                )
                result = eid
            elif action == "prescribe":
                eid = ident(p, "encounter_id")
                e = encounter(c, eid, True)
                result = insert(
                    c,
                    "Prescription",
                    {
                        "patient_id": e["patient_id"],
                        "doctor_id": e["doctor_id"],
                        "medicine_id": ident(p, "medicine_id"),
                        "dosage": text(p, "dosage", 200),
                        "duration": text(p, "duration", 100),
                        "prescription_date": datetime.combine(
                            hospital_today(), datetime.min.time()
                        ),
                        "encounter_id": eid,
                        "ordered_quantity": _parse_integer(
                            p.get("ordered_quantity"),
                            "ordered_quantity",
                            minimum=1,
                            maximum=100000,
                        ),
                    },
                    "prescription_id",
                )
            elif action == "order_test":
                eid = ident(p, "encounter_id")
                encounter(c, eid, True)
                tid = ident(p, "test_id")
                t = row(
                    c,
                    "SELECT test_name,fee FROM HMS_Test_Catalog WHERE test_id=:id AND is_active='Y'",
                    {"id": tid},
                )
                result = insert(
                    c,
                    "HMS_Test_Order",
                    {"encounter_id": eid, "test_id": tid},
                    "order_id",
                )
                care_charge(
                    c, eid, "Test", result, t["test_name"], 1, Decimal(str(t["fee"]))
                )
            elif action == "result":
                oid = ident(p, "order_id")
                t = row(
                    c,
                    "SELECT status FROM HMS_Test_Order WHERE order_id=:id",
                    {"id": oid},
                )
                if t["status"] != "Ordered":
                    raise ApiError(
                        "Result already retained; duplicate result blocked.",
                        409,
                        "result_exists",
                    )
                c.execute(
                    "SELECT cancellation_id FROM HMS_Order_Cancel WHERE order_id=:id",
                    {"id": oid},
                )
                if c.fetchone():
                    raise ApiError("Test order was cancelled.", 409, "order_cancelled")
                result = insert(
                    c,
                    "HMS_Test_Result",
                    {
                        "order_id": oid,
                        "user_id": uid,
                        "result_text": text(p, "result_text", 2000),
                    },
                    "result_id",
                )
                c.execute(
                    "UPDATE HMS_Test_Order SET status='Resulted' WHERE order_id=:id",
                    {"id": oid},
                )
            elif action == "observation":
                aid = ident(p, "admission_id")
                a = row(
                    c,
                    "SELECT patient_id,discharge_date FROM Admission WHERE admission_id=:id",
                    {"id": aid},
                )
                check_patient(int(a["patient_id"]), c)
                if a["discharge_date"] is not None:
                    raise ApiError("Admission is discharged.", 409, "admission_closed")
                result = insert(
                    c,
                    "HMS_Observation",
                    {
                        "admission_id": aid,
                        "user_id": uid,
                        "observation": text(p, "observation", 2000),
                    },
                    "observation_id",
                )
            elif action == "receive_batch":
                mid = ident(p, "medicine_id")
                qty = _parse_integer(
                    p.get("quantity"), "quantity", minimum=1, maximum=100000
                )
                expiry = _validate_date(p.get("expires_on"), "expires_on")
                if expiry.date() < hospital_today():
                    raise ApiError("Do not receive already expired stock.")
                row(
                    c,
                    "SELECT medicine_id FROM Medicine WHERE medicine_id=:id",
                    {"id": mid},
                )
                # New consignment, never an allocation of unproven old stock.
                batch_number = text(p, "batch_number", 60)
                c.execute(
                    "SELECT batch_id,expires_on FROM HMS_Medicine_Batch WHERE medicine_id=:mid AND batch_number=:number",
                    {"mid": mid, "number": batch_number},
                )
                existing = c.fetchone()
                if existing:
                    if str(existing[1])[:10] != expiry.date().isoformat():
                        raise ApiError(
                            "This batch already has a different recorded expiry; investigate instead of rewriting its history.",
                            409,
                            "batch_expiry_conflict",
                        )
                    result = int(existing[0])
                    c.execute(
                        "UPDATE HMS_Medicine_Batch SET quantity=quantity+:qty WHERE batch_id=:id",
                        {"qty": qty, "id": result},
                    )
                else:
                    result = insert(
                        c,
                        "HMS_Medicine_Batch",
                        {
                            "medicine_id": mid,
                            "batch_number": batch_number,
                            "expires_on": expiry,
                            "quantity": qty,
                        },
                        "batch_id",
                    )
                c.execute(
                    "UPDATE Medicine SET stock_quantity=stock_quantity+:qty WHERE medicine_id=:id",
                    {"qty": qty, "id": mid},
                )
                from .corrections import stock_event

                stock_event(
                    c,
                    kind="RECEIPT",
                    medicine_id=mid,
                    batch_id=result,
                    quantity=qty,
                    user_id=uid,
                    reason="New batch receipt: " + text(p, "batch_number", 60),
                )
            elif action == "dispense":
                rxid = ident(p, "prescription_id")
                bid = ident(p, "batch_id")
                qty = _parse_integer(
                    p.get("quantity"), "quantity", minimum=1, maximum=100000
                )
                key = str(p.get("idempotency_key", "")).lower()
                if not re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}", key):
                    raise ApiError("Supply UUID idempotency_key.")
                c.execute(
                    "SELECT dispense_id,prescription_id,batch_id,quantity FROM HMS_Dispense WHERE idempotency_key=:key",
                    {"key": key},
                )
                old = c.fetchone()
                if old:
                    if tuple(int(v) for v in old[1:]) != (rxid, bid, qty):
                        raise ApiError(
                            "Dispensing key payload mismatch.",
                            409,
                            "idempotency_mismatch",
                        )
                    return jsonify({"data": {"id": int(old[0]), "replayed": True}})
                c.execute(
                    "SELECT cancellation_id FROM HMS_Order_Cancel WHERE prescription_id=:id",
                    {"id": rxid},
                )
                if c.fetchone():
                    raise ApiError(
                        "Remaining prescription was cancelled.", 409, "order_cancelled"
                    )
                rx = row(
                    c,
                    "SELECT r.medicine_id,r.ordered_quantity,r.encounter_id,m.price,m.medicine_name FROM Prescription r JOIN Medicine m ON m.medicine_id=r.medicine_id WHERE r.prescription_id=:id",
                    {"id": rxid},
                )
                if not rx["ordered_quantity"] or not rx["encounter_id"]:
                    raise ApiError(
                        "Legacy order needs a new clinician quantity/context; no inferred dispensing.",
                        409,
                        "quantity_missing",
                    )
                b = row(
                    c,
                    "SELECT medicine_id,expires_on,quantity FROM HMS_Medicine_Batch WHERE batch_id=:id",
                    {"id": bid},
                )
                if int(b["medicine_id"]) != int(rx["medicine_id"]):
                    raise ApiError("Batch medicine does not match prescription.")
                if str(b["expires_on"])[:10] < hospital_today().isoformat():
                    raise ApiError("Batch is expired.", 409, "expired_batch")
                c.execute(
                    "SELECT NVL(SUM(quantity),0) FROM HMS_Dispense WHERE prescription_id=:id",
                    {"id": rxid},
                )
                done = int(c.fetchone()[0])
                if done + qty > int(rx["ordered_quantity"]) or qty > int(b["quantity"]):
                    raise ApiError(
                        "Quantity exceeds remaining order or batch balance.",
                        409,
                        "insufficient_quantity",
                    )
                c.execute(
                    "UPDATE HMS_Medicine_Batch SET quantity=quantity-:qty WHERE batch_id=:id",
                    {"qty": qty, "id": bid},
                )
                c.execute(
                    "UPDATE Medicine SET stock_quantity=stock_quantity-:qty WHERE medicine_id=:id",
                    {"qty": qty, "id": rx["medicine_id"]},
                )
                result = insert(
                    c,
                    "HMS_Dispense",
                    {
                        "prescription_id": rxid,
                        "batch_id": bid,
                        "user_id": uid,
                        "quantity": qty,
                        "idempotency_key": key,
                    },
                    "dispense_id",
                )
                from .corrections import assert_stock

                assert_stock(c)
                care_charge(
                    c,
                    rx["encounter_id"],
                    "Dispense",
                    result,
                    rx["medicine_name"],
                    qty,
                    Decimal(str(rx["price"])),
                )
            elif action == "prepare_bill":
                eid = ident(p, "encounter_id") if p.get("encounter_id") else None
                aid = ident(p, "admission_id") if p.get("admission_id") else None
                if bool(eid) == bool(aid):
                    raise ApiError("Choose exactly one encounter or admission.")
                if eid:
                    e = row(
                        c,
                        "SELECT patient_id,status FROM HMS_Encounter WHERE encounter_id=:id",
                        {"id": eid},
                    )
                    pid = e["patient_id"]
                    condition = "ch.encounter_id=:context"
                    context = eid
                    if e["status"] != "Completed":
                        raise ApiError(
                            "Complete the consultation before final billing.",
                            409,
                            "care_unfinished",
                        )
                else:
                    if "room_charge" not in p:
                        raise ApiError(
                            "Provide the agreed room charge explicitly, including zero if waived; no historical tariff is inferred."
                        )
                    e = row(
                        c,
                        "SELECT patient_id,discharge_date FROM Admission WHERE admission_id=:id",
                        {"id": aid},
                    )
                    pid = e["patient_id"]
                    condition = "ec.admission_id=:context"
                    context = aid
                    if e["discharge_date"] is None:
                        raise ApiError(
                            "Discharge before final inpatient bill.",
                            409,
                            "not_discharged",
                        )
                where = "e.encounter_id=:context" if eid else "e.admission_id=:context"
                c.execute(
                    "SELECT COUNT(*) FROM HMS_Test_Order t JOIN HMS_Encounter e ON e.encounter_id=t.encounter_id WHERE t.status='Ordered' AND NOT EXISTS(SELECT 1 FROM HMS_Order_Cancel x WHERE x.order_id=t.order_id) AND "
                    + where,
                    {"context": context},
                )
                if c.fetchone()[0]:
                    raise ApiError(
                        "Pending test results must be resolved before final billing.",
                        409,
                        "care_unfinished",
                    )
                c.execute(
                    "SELECT COUNT(*) FROM Prescription rx JOIN HMS_Encounter e ON e.encounter_id=rx.encounter_id WHERE NOT EXISTS(SELECT 1 FROM HMS_Order_Cancel x WHERE x.prescription_id=rx.prescription_id) AND rx.ordered_quantity>NVL((SELECT SUM(d.quantity) FROM HMS_Dispense d WHERE d.prescription_id=rx.prescription_id),0) AND "
                    + where,
                    {"context": context},
                )
                if c.fetchone()[0]:
                    raise ApiError(
                        "Pending dispensing must be resolved before final billing.",
                        409,
                        "care_unfinished",
                    )
                context_col = "encounter_id" if eid else "admission_id"
                c.execute(
                    "SELECT COUNT(*) FROM Bill WHERE " + context_col + "=:context",
                    {"context": context},
                )
                if c.fetchone()[0]:
                    raise ApiError(
                        "Final invoice already exists for this care context.",
                        409,
                        "already_billed",
                    )
                c.execute(
                    "SELECT ch.charge_id,ch.description,ch.quantity,ch.unit_price FROM V_HMS_Care_Net ch JOIN HMS_Encounter ec ON ec.encounter_id=ch.encounter_id WHERE ch.bill_item_id IS NULL AND ch.quantity>0 AND "
                    + condition,
                    {"context": context},
                )
                charges = _fetch_rows(c)
                room_fee = money(p, "room_charge")
                if not charges and room_fee == 0:
                    raise ApiError(
                        "No unbilled care charges; do not duplicate invoices.",
                        409,
                        "no_unbilled_charges",
                    )
                vals = {
                    "patient_id": pid,
                    "bill_date": datetime.combine(
                        hospital_today(), datetime.min.time()
                    ),
                    "consultation_charge": Decimal("0"),
                    "room_charge": room_fee,
                    "medicine_charge": Decimal("0"),
                    "notes": text(p, "notes", 300, False),
                    "encounter_id": eid,
                    "admission_id": aid,
                }
                result = insert(c, "Bill", vals, "bill_id")
                for ch in charges:
                    item = insert(
                        c,
                        "Bill_Item",
                        {
                            "bill_id": result,
                            "description": ch["description"],
                            "quantity": int(ch["quantity"]),
                            "unit_price": Decimal(str(ch["unit_price"])),
                        },
                        "item_id",
                    )
                    c.execute(
                        "UPDATE HMS_Care_Charge SET bill_item_id=:item WHERE charge_id=:id",
                        {"item": item, "id": ch["charge_id"]},
                    )
            elif action == "maintenance_request":
                result = insert(
                    c,
                    "HMS_Maintenance_Task",
                    {
                        "room_id": ident(p, "room_id"),
                        "description": text(p, "description", 300),
                        "created_by": uid,
                    },
                    "task_id",
                )
            elif action in ("maintenance_start", "maintenance_complete"):
                tid = ident(p, "task_id")
                t = row(
                    c,
                    "SELECT room_id,status FROM HMS_Maintenance_Task WHERE task_id=:id",
                    {"id": tid},
                )
                expected = "Open" if action == "maintenance_start" else "InProgress"
                if t["status"] != expected:
                    raise ApiError(
                        "Task is not in the required state.", 409, "task_state"
                    )
                if action == "maintenance_start":
                    c.execute(
                        "SELECT COUNT(*) FROM HMS_Maintenance_Task WHERE room_id=:room AND status='InProgress'",
                        {"room": t["room_id"]},
                    )
                    if c.fetchone()[0]:
                        raise ApiError(
                            "Room already has work in progress.",
                            409,
                            "maintenance_busy",
                        )
                room = row(
                    c,
                    "SELECT availability_status FROM Room WHERE room_id=:id",
                    {"id": t["room_id"]},
                )
                expected_room = (
                    "Available" if action == "maintenance_start" else "Maintenance"
                )
                if room["availability_status"] != expected_room:
                    raise ApiError(
                        "Room is not available for this task transition.",
                        409,
                        "room_unavailable",
                    )
                c.execute(
                    "UPDATE Room SET availability_status=:status WHERE room_id=:id",
                    {
                        "status": "Maintenance"
                        if action == "maintenance_start"
                        else "Available",
                        "id": t["room_id"],
                    },
                )
                if action == "maintenance_start":
                    c.execute(
                        "UPDATE HMS_Maintenance_Task SET status='InProgress' WHERE task_id=:id",
                        {"id": tid},
                    )
                if action == "maintenance_complete":
                    c.execute(
                        "UPDATE HMS_Maintenance_Task SET status='Completed',completed_by=:uid WHERE task_id=:id",
                        {"uid": uid, "id": tid},
                    )
                result = tid
            if receipt_key:
                c.execute(
                    "INSERT INTO HMS_Operation(operation_key,user_id,action,payload_hash,result_id,reason) VALUES(:key,:uid,:action,:hash,:result,:reason)",
                    {
                        "key": receipt_key,
                        "uid": uid,
                        "action": action,
                        "hash": receipt_hash,
                        "result": result,
                        "reason": "New verified batch receipt",
                    },
                )
            audit(
                c,
                action,
                "workflow",
                rid if action == "review_request" else result or 0,
            )
    return jsonify({"data": {"id": result, "saved": True}}), 201
