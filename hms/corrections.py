"""Reasoned corrective events. Original clinical, stock and receipt facts survive."""

from __future__ import annotations

import hashlib
import json
import uuid
from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from .api import (
    ApiError,
    _db,
    _fetch_rows,
    _lock_bill,
    _request_json,
    _snapshot,
    _transaction,
    hospital_today,
)
from .auth import audit, require
from .workflows import ident, insert, money, row, text

corrections = Blueprint("corrections", __name__)
ROLES = {
    "amend_consultation": ("doctor", "manager"),
    "amend_result": ("lab", "manager"),
    "cancel_rx": ("doctor", "manager"),
    "cancel_test": ("doctor", "manager"),
    "return_stock": ("pharmacist", "manager"),
    "write_off": ("pharmacist", "manager"),
    "adjust_add": ("manager",),
    "adjust_remove": ("manager",),
    "credit": ("manager",),
    "debit": ("manager",),
    "writeoff": ("manager",),
    "refund": ("manager", "cashier"),
    "void_invoice": ("manager",),
    "profile": ("patient",),
    "cancel_appointment": ("patient",),
    "reschedule_appointment": ("patient",),
}
FIELDS = {
    "amend_consultation": {"encounter_id", "content", "reason"},
    "amend_result": {"result_id", "content", "reason"},
    "cancel_rx": {"prescription_id", "reason"},
    "cancel_test": {"order_id", "reason"},
    "return_stock": {"dispense_id", "quantity", "disposition", "reason"},
    "write_off": {"batch_id", "quantity", "reason"},
    "adjust_add": {"batch_id", "quantity", "reason"},
    "adjust_remove": {"batch_id", "quantity", "reason"},
    "credit": {"bill_id", "amount", "reason"},
    "debit": {"bill_id", "amount", "reason"},
    "writeoff": {"bill_id", "amount", "reason"},
    "refund": {"bill_id", "payment_id", "amount", "reason"},
    "void_invoice": {"bill_id", "reason"},
    "profile": {"phone", "address"},
    "cancel_appointment": {"appointment_id", "reason"},
    "reschedule_appointment": {
        "appointment_id",
        "appointment_date",
        "appointment_time",
        "reason",
    },
}


def clinical_owner(c, eid):
    e = row(
        c,
        "SELECT encounter_id,patient_id,doctor_id,status FROM HMS_Encounter WHERE encounter_id=:id",
        {"id": eid},
    )
    if g.user["role"] == "doctor" and e["doctor_id"] != g.user["doctor_id"]:
        raise ApiError("Clinical record not found.", 404, "not_found")
    return e


def unavailable(message):
    raise ApiError(message, 409, "invalid_transition")


def stock_event(
    c, *, kind, medicine_id, batch_id, quantity, user_id, reason, dispense_id=None
):
    result = insert(
        c,
        "HMS_Stock_Event",
        dict(
            event_kind=kind,
            medicine_id=medicine_id,
            batch_id=batch_id,
            quantity=quantity,
            user_id=user_id,
            reason=reason,
            dispense_id=dispense_id,
        ),
        "event_id",
    )
    assert_stock(c)
    return result


def assert_stock(c):
    for view in ("V_HMS_Batch_Recon", "V_HMS_Medicine_Recon"):
        c.execute("SELECT COUNT(*) FROM " + view + " WHERE difference<>0")
        if int(c.fetchone()[0]):
            unavailable(
                "Stock journal does not reconcile; operation rolled back. Investigate the observed history."
            )


@corrections.post("/api/corrections/<string:action>")
def correct(action, payload=None):
    if action not in ROLES:
        raise ApiError("Unknown correction.", 404, "not_found")
    require(*ROLES[action])
    p = _request_json() if payload is None else dict(payload)
    optional = (
        {"stock_event_id"} if action in ("credit", "writeoff", "refund") else set()
    )
    if not FIELDS[action] | {"idempotency_key"} <= set(p) or set(p) - (
        FIELDS[action] | {"idempotency_key"} | optional
    ):
        raise ApiError(
            "Supply exactly: " + ", ".join(sorted(FIELDS[action] | {"idempotency_key"}))
        )
    try:
        key = str(uuid.UUID(str(p.pop("idempotency_key"))))
    except (ValueError, TypeError, AttributeError):
        raise ApiError("A UUID idempotency_key is required.") from None
    fingerprint = hashlib.sha256(
        json.dumps(
            {"action": action, "payload": p}, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    uid = g.user["user_id"]
    reason = (
        text(p, "reason", 500)
        if "reason" in p
        else "Patient self-service contact update"
    )
    with _transaction(_db()) as conn:
        with conn.cursor() as c:
            # _transaction takes the bounded global mutex and revalidates the live actor.
            require(*ROLES[action])
            c.execute(
                "SELECT user_id,action,payload_hash,result_id FROM HMS_Operation WHERE operation_key=:key",
                {"key": key},
            )
            old = c.fetchone()
            if old:
                if (int(old[0]), old[1], old[2]) != (uid, action, fingerprint):
                    raise ApiError(
                        "This key belongs to different request details or actor.",
                        409,
                        "idempotency_mismatch",
                    )
                return jsonify(data={"id": int(old[3]), "replayed": True}), 200
            if action in ("amend_consultation", "amend_result"):
                eid = (
                    ident(p, "encounter_id") if action == "amend_consultation" else None
                )
                rid = ident(p, "result_id") if action == "amend_result" else None
                if eid:
                    if clinical_owner(c, eid)["status"] != "Completed":
                        unavailable(
                            "Complete the original consultation before appending an amendment."
                        )
                else:
                    row(
                        c,
                        "SELECT result_id FROM HMS_Test_Result WHERE result_id=:id",
                        {"id": rid},
                    )
                result = insert(
                    c,
                    "HMS_Amendment",
                    dict(
                        encounter_id=eid,
                        result_id=rid,
                        content=text(p, "content", 2000),
                        reason=reason,
                        user_id=uid,
                    ),
                    "amendment_id",
                )
            elif action in ("cancel_rx", "cancel_test"):
                rxid = ident(p, "prescription_id") if action == "cancel_rx" else None
                oid = ident(p, "order_id") if action == "cancel_test" else None
                order = row(
                    c,
                    (
                        "SELECT encounter_id FROM Prescription WHERE prescription_id=:id"
                        if rxid
                        else "SELECT encounter_id,status FROM HMS_Test_Order WHERE order_id=:id"
                    ),
                    {"id": rxid or oid},
                )
                if not order["encounter_id"]:
                    unavailable(
                        "Unlinked historical instructions cannot be cancelled as clinical orders."
                    )
                clinical_owner(c, order["encounter_id"])
                if rxid:
                    c.execute(
                        "SELECT ordered_quantity-NVL((SELECT SUM(quantity) FROM HMS_Dispense d WHERE d.prescription_id=rx.prescription_id),0) FROM Prescription rx WHERE prescription_id=:id",
                        {"id": rxid},
                    )
                    if int(c.fetchone()[0]) <= 0:
                        unavailable(
                            "Prescription is already fulfilled; record a return or create a new clinical order."
                        )
                if oid and order["status"] != "Ordered":
                    unavailable(
                        "A completed test cannot be cancelled; append a result amendment."
                    )
                c.execute(
                    "SELECT cancellation_id FROM HMS_Order_Cancel WHERE "
                    + ("prescription_id" if rxid else "order_id")
                    + "=:id",
                    {"id": rxid or oid},
                )
                if c.fetchone():
                    unavailable("The remaining order is already cancelled.")
                if oid:
                    c.execute(
                        "SELECT charge_id FROM HMS_Care_Charge WHERE source_kind='Test' AND source_id=:id AND bill_item_id IS NOT NULL",
                        {"id": oid},
                    )
                    if c.fetchone():
                        unavailable(
                            "Billed tests require a separate financial correction."
                        )
                result = insert(
                    c,
                    "HMS_Order_Cancel",
                    dict(
                        prescription_id=rxid, order_id=oid, reason=reason, user_id=uid
                    ),
                    "cancellation_id",
                )
            elif action in ("return_stock", "write_off", "adjust_add", "adjust_remove"):
                qty = ident(p, "quantity")
                if qty > 100000:
                    raise ApiError("Quantity must not exceed100000.")
                disp = None
                if action == "return_stock":
                    disp = ident(p, "dispense_id")
                    d = row(
                        c,
                        "SELECT d.batch_id,d.quantity,b.medicine_id,b.expires_on FROM HMS_Dispense d JOIN HMS_Medicine_Batch b ON b.batch_id=d.batch_id WHERE d.dispense_id=:id",
                        {"id": disp},
                    )
                    c.execute(
                        "SELECT NVL(SUM(quantity),0) FROM HMS_Stock_Event WHERE dispense_id=:id AND event_kind IN ('RETURN_RESTOCK','RETURN_QUARANTINE')",
                        {"id": disp},
                    )
                    if qty > int(d["quantity"]) - int(c.fetchone()[0]):
                        unavailable(
                            "Return exceeds the original unreturned dispense quantity."
                        )
                    disposition = text(p, "disposition", 20)
                    if disposition not in ("Restock", "Quarantine"):
                        raise ApiError("Choose Restock or Quarantine.")
                    kind = (
                        "RETURN_RESTOCK"
                        if disposition == "Restock"
                        else "RETURN_QUARANTINE"
                    )
                    bid = d["batch_id"]
                    mid = d["medicine_id"]
                    delta = qty if disposition == "Restock" else 0
                else:
                    bid = ident(p, "batch_id")
                    d = row(
                        c,
                        "SELECT medicine_id,quantity,expires_on FROM HMS_Medicine_Batch WHERE batch_id=:id",
                        {"id": bid},
                    )
                    mid = d["medicine_id"]
                    delta = qty if action == "adjust_add" else -qty
                    kind = {
                        "write_off": "WRITE_OFF",
                        "adjust_add": "ADJUST_ADD",
                        "adjust_remove": "ADJUST_REMOVE",
                    }[action]
                expiry = d["expires_on"]
                if delta > 0 and str(expiry)[:10] < hospital_today().isoformat():
                    unavailable(
                        "Expired returns must be quarantined; expired stock cannot be added to available inventory."
                    )
                if delta:
                    c.execute(
                        "UPDATE HMS_Medicine_Batch SET quantity=quantity+:delta WHERE batch_id=:id AND quantity+:delta>=0",
                        {"delta": delta, "id": bid},
                    )
                    if c.rowcount != 1:
                        unavailable("Movement exceeds available batch quantity.")
                    c.execute(
                        "UPDATE Medicine SET stock_quantity=stock_quantity+:delta WHERE medicine_id=:id AND stock_quantity+:delta>=0",
                        {"delta": delta, "id": mid},
                    )
                    if c.rowcount != 1:
                        unavailable("Movement exceeds aggregate stock.")
                result = stock_event(
                    c,
                    kind=kind,
                    medicine_id=mid,
                    batch_id=bid,
                    quantity=qty,
                    user_id=uid,
                    reason=reason,
                    dispense_id=disp,
                )
                c.execute(
                    "SELECT difference FROM V_HMS_Batch_Recon WHERE batch_id=:id",
                    {"id": bid},
                )
                if Decimal(str(c.fetchone()[0])) != 0:
                    unavailable(
                        "Stock journal does not reconcile; correction rolled back. Investigate without rewriting history."
                    )
            elif action in ("credit", "debit", "writeoff", "refund", "void_invoice"):
                bid = ident(p, "bill_id")
                _lock_bill(c, bid)
                b = row(
                    c,
                    "SELECT billed,paid,balance,ledger_status FROM V_Invoice_Balances WHERE bill_id=:id",
                    {"id": bid},
                )
                if b["ledger_status"] == "Voided":
                    unavailable("A void invoice cannot be reopened.")
                amount = (
                    Decimal(str(b["balance"]))
                    if action == "void_invoice"
                    else money(p, "amount")
                )
                if amount <= 0:
                    raise ApiError("Correction amount must be positive.")
                if action in (
                    "credit",
                    "writeoff",
                    "void_invoice",
                ) and amount > Decimal(str(b["balance"])):
                    unavailable(
                        "Credit/write-off exceeds the outstanding balance; paid charges need a linked refund."
                    )
                if action == "void_invoice":
                    c.execute(
                        "SELECT COUNT(*) FROM Bill_Payment WHERE bill_id=:id",
                        {"id": bid},
                    )
                    if c.fetchone()[0]:
                        unavailable(
                            "An invoice with receipt history cannot be voided; use explicit financial corrections."
                        )
                    c.execute(
                        "SELECT COUNT(*) FROM Bill WHERE bill_id=:id AND (encounter_id IS NOT NULL OR admission_id IS NOT NULL)",
                        {"id": bid},
                    )
                    if c.fetchone()[0]:
                        unavailable(
                            "Clinical final invoices cannot be voided. Use reasoned credits/write-offs; retain the finalization link."
                        )
                stock_id = (
                    ident(p, "stock_event_id") if p.get("stock_event_id") else None
                )
                if g.user["role"] == "cashier" and not stock_id:
                    raise ApiError(
                        "Cashiers may refund only a recorded billed medicine return at its uncredited original price. Other corrections require a manager.",
                        403,
                        "forbidden",
                    )
                if stock_id:
                    review = row(
                        c,
                        "SELECT bill_id,remaining_credit FROM V_HMS_Return_Review WHERE event_id=:id",
                        {"id": stock_id},
                    )
                    if int(review["bill_id"]) != bid:
                        raise ApiError(
                            "Return does not belong to this invoice.", 404, "not_found"
                        )
                    if amount > Decimal(str(review["remaining_credit"])):
                        unavailable(
                            "Linked return credit exceeds its uncorrected original-price value."
                        )
                payment = None

                def financial(kind):
                    return insert(
                        c,
                        "HMS_Fin_Event",
                        dict(
                            bill_id=bid,
                            event_kind=kind,
                            amount=amount,
                            payment_id=payment,
                            related_event_id=result
                            if kind == "REFUND_CREDIT"
                            else None,
                            stock_event_id=stock_id,
                            user_id=uid,
                            reason=reason,
                        ),
                        "event_id",
                    )

                if action == "refund":
                    payment = ident(p, "payment_id")
                    receipt = row(
                        c,
                        "SELECT amount FROM Bill_Payment WHERE payment_id=:pay AND bill_id=:bill",
                        {"pay": payment, "bill": bid},
                    )
                    c.execute(
                        "SELECT NVL(SUM(amount),0) FROM HMS_Fin_Event WHERE payment_id=:id AND event_kind='REFUND'",
                        {"id": payment},
                    )
                    if amount > Decimal(str(receipt["amount"])) - Decimal(
                        str(c.fetchone()[0])
                    ) or amount > Decimal(str(b["paid"])):
                        unavailable(
                            "Refund exceeds this receipt’s unrefunded net collection."
                        )
                    # Cash out first, price credit second; both commit or neither does.
                    result = financial("REFUND")
                    payment = None
                    financial("REFUND_CREDIT")
                else:
                    if action == "debit" and Decimal(
                        str(b["billed"])
                    ) + amount > Decimal("999999999.99"):
                        raise ApiError("Corrected invoice exceeds the monetary limit.")
                    result = financial(
                        {
                            "credit": "CREDIT",
                            "debit": "DEBIT",
                            "writeoff": "WRITE_OFF",
                            "void_invoice": "VOID",
                        }[action]
                    )
            elif action == "profile":
                # Identity is exclusively from the revalidated personal session.
                result = g.user["patient_id"]
                c.execute(
                    "UPDATE Patient SET phone=:phone,address=:address WHERE patient_id=:id",
                    {
                        "phone": text(p, "phone", 20, False),
                        "address": text(p, "address", 300, False),
                        "id": result,
                    },
                )
            else:
                aid = ident(p, "appointment_id")
                appointment = row(
                    c,
                    "SELECT patient_id,doctor_id,status,appointment_date,duration_minutes FROM Appointment WHERE appointment_id=:id",
                    {"id": aid},
                )
                if appointment["patient_id"] != g.user["patient_id"]:
                    raise ApiError("Appointment not found.", 404, "not_found")
                if (
                    str(appointment["appointment_date"])[:10]
                    < hospital_today().isoformat()
                ):
                    unavailable("Past appointments are retained history.")
                if appointment["status"] != "Scheduled":
                    unavailable(
                        "Only a future Scheduled appointment may be changed by its patient."
                    )
                if action == "cancel_appointment":
                    c.execute(
                        "UPDATE Appointment SET status='Cancelled' WHERE appointment_id=:id",
                        {"id": aid},
                    )
                else:
                    from .api import (
                        RESOURCES,
                        _check_doctor_slot,
                        _validate_payload,
                        _validate_scheduled_appointment,
                    )

                    values = _validate_payload(
                        RESOURCES["appointments"],
                        {
                            "appointment_date": p["appointment_date"],
                            "appointment_time": p["appointment_time"],
                        },
                        partial=True,
                    )
                    values.update(
                        patient_id=appointment["patient_id"],
                        doctor_id=appointment["doctor_id"],
                    )
                    values["duration_minutes"] = int(appointment["duration_minutes"])
                    _validate_scheduled_appointment(values)
                    _check_doctor_slot(c, values, aid)
                    c.execute(
                        "UPDATE Appointment SET appointment_date=:appointment_date,appointment_time=:appointment_time WHERE appointment_id=:id",
                        {
                            "appointment_date": values["appointment_date"],
                            "appointment_time": values["appointment_time"],
                            "id": aid,
                        },
                    )
                result = aid
            c.execute(
                "INSERT INTO HMS_Operation(operation_key,user_id,action,payload_hash,result_id,reason) VALUES(:key,:uid,:action,:hash,:result,:reason)",
                {
                    "key": key,
                    "uid": uid,
                    "action": action,
                    "hash": fingerprint,
                    "result": result,
                    "reason": reason,
                },
            )
            audit(c, "correction:" + action, action, result)
    return jsonify(data={"id": result, "replayed": False}), 201


@corrections.get("/api/corrections/history")
def history():
    require(
        *tuple(
            ROLES["amend_consultation"]
            + ("patient", "lab", "pharmacist", "cashier", "nurse")
        )
    )
    from .auth import patient_scope

    role = g.user["role"]
    data = {}
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        raise ApiError("Invalid history page.") from None
    if page > 100000:
        raise ApiError("History page exceeds100000.")
    offset = (page - 1) * 40
    data["counts"] = {}
    with _snapshot() as conn:
        with conn.cursor() as c:

            def read(name, sql, binds=None):
                c.execute("SELECT COUNT(*) FROM (" + sql + ") h", binds or {})
                data["counts"][name] = int(c.fetchone()[0])
                c.execute(
                    "SELECT * FROM ("
                    + sql
                    + ") h ORDER BY 1 DESC OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY",
                    {**(binds or {}), "offset": offset, "limit": 40},
                )
                data[name] = _fetch_rows(c)

            if role in ("manager", "doctor", "patient", "nurse", "lab"):
                scope, binds = (
                    patient_scope("e")
                    if role in ("doctor", "patient", "nurse")
                    else ("1=1", {})
                )
                # Patients only see completed consultation/result amendments, not working notes.
                if role == "patient":
                    scope += " AND e.status='Completed'"
                # Results link through test orders (not an invented result.encounter_id).
                read(
                    "amendments",
                    "SELECT a.amendment_id,a.encounter_id,a.result_id,e.patient_id,a.content,a.reason,a.user_id,a.recorded_at FROM HMS_Amendment a LEFT JOIN HMS_Test_Result r ON r.result_id=a.result_id LEFT JOIN HMS_Test_Order t ON t.order_id=r.order_id JOIN HMS_Encounter e ON e.encounter_id=COALESCE(a.encounter_id,t.encounter_id) WHERE "
                    + scope
                    + (" AND a.result_id IS NOT NULL" if role == "lab" else ""),
                    binds,
                )
            if role in ("manager", "doctor", "patient", "pharmacist", "lab"):
                scope, binds = (
                    patient_scope("e") if role in ("doctor", "patient") else ("1=1", {})
                )
                if role == "pharmacist":
                    scope += " AND x.prescription_id IS NOT NULL"
                if role == "lab":
                    scope += " AND x.order_id IS NOT NULL"
                read(
                    "cancellations",
                    "SELECT x.cancellation_id,x.prescription_id,x.order_id,e.patient_id,x.reason,x.user_id,x.recorded_at FROM HMS_Order_Cancel x LEFT JOIN Prescription rx ON rx.prescription_id=x.prescription_id LEFT JOIN HMS_Test_Order t ON t.order_id=x.order_id JOIN HMS_Encounter e ON e.encounter_id=COALESCE(rx.encounter_id,t.encounter_id) WHERE "
                    + scope,
                    binds,
                )
            if role in ("manager", "pharmacist"):
                read(
                    "stock_events",
                    "SELECT event_id,event_kind,medicine_id,batch_id,dispense_id,quantity,reason,user_id,recorded_at FROM HMS_Stock_Event",
                )
                read(
                    "reconciliation",
                    "SELECT batch_id,medicine_id,quantity,expected_quantity,difference FROM V_HMS_Batch_Recon",
                )
                read(
                    "aggregate_reconciliation",
                    "SELECT medicine_id,stock_quantity,expected_quantity,difference,legacy_quantity FROM V_HMS_Medicine_Recon",
                )
            if role in ("manager", "cashier", "patient"):
                scope, binds = patient_scope("b") if role == "patient" else ("1=1", {})
                read(
                    "financial_events",
                    "SELECT f.event_id,f.bill_id,b.patient_id,f.event_kind,f.amount,f.payment_id,f.related_event_id,f.stock_event_id,f.reason,f.user_id,f.recorded_at FROM HMS_Fin_Event f JOIN Bill b ON b.bill_id=f.bill_id WHERE "
                    + scope,
                    binds,
                )
    return jsonify(data={**data, "page": page, "page_size": 40})
