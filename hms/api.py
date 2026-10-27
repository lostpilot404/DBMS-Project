"""Parameterized JSON API for the Hospital Management System."""
from __future__ import annotations

import csv
import io
import re
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request


api = Blueprint("api", __name__)


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "invalid_request") -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def _field(kind: str, *, required: bool = False, max_length: int | None = None,
           choices: tuple[str, ...] | None = None, default: Any = None,
           nullable: bool = True) -> dict[str, Any]:
    return {
        "type": kind,
        "required": required,
        "max_length": max_length,
        "choices": choices,
        "default": default,
        "nullable": nullable,
    }


GENDERS = ("M", "F", "O")
BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
APPOINTMENT_STATUSES = (
    "Scheduled", "Checked In", "Waiting", "In Consultation",
    "Completed", "Cancelled", "No-show",
)
APPOINTMENT_TRANSITIONS = {
    "Scheduled": ("Checked In", "Cancelled", "No-show"),
    "Checked In": ("Waiting",),
    "Waiting": ("In Consultation",),
    "In Consultation": ("Completed",),
    "Completed": (),
    "Cancelled": (),
    "No-show": (),
}
ROOM_STATUSES = ("Available", "Occupied", "Maintenance")
BILL_STATUSES = ("Paid", "Pending")

# Every table/column/SQL fragment here is a constant controlled by the application.
# User values are always bound parameters; arbitrary identifiers never enter SQL.
RESOURCES: dict[str, dict[str, Any]] = {
    "departments": {
        "table": "Department", "id": "department_id", "alias": "d",
        "select": "SELECT d.department_id AS department_id, d.department_name AS department_name, "
                  "d.location AS location, (SELECT COUNT(*) FROM Doctor dc "
                  "WHERE dc.department_id = d.department_id) AS doctor_count, "
                  "(SELECT LISTAGG(dc.doctor_name, ', ') WITHIN GROUP (ORDER BY dc.doctor_name) "
                  "FROM Doctor dc WHERE dc.department_id = d.department_id) AS associated_doctors "
                  "FROM Department d",
        "order": "d.department_name, d.department_id",
        "sorts": {"department_name": "d.department_name", "location": "d.location", "doctor_count": "doctor_count"},
        "search": ["UPPER(d.department_name) LIKE :q", "UPPER(d.location) LIKE :q"],
        "filters": {},
        "fields": {
            "department_name": _field("string", required=True, max_length=100, nullable=False),
            "location": _field("string", required=True, max_length=150, nullable=False),
        },
    },
    "doctors": {
        "table": "Doctor", "id": "doctor_id", "alias": "d",
        "select": "SELECT d.doctor_id AS doctor_id, d.doctor_name AS doctor_name, "
                  "d.specialization AS specialization, d.phone AS phone, d.email AS email, "
                  "d.department_id AS department_id, dep.department_name AS department_name "
                  "FROM Doctor d JOIN Department dep ON dep.department_id = d.department_id",
        "order": "d.doctor_name, d.doctor_id",
        "sorts": {"doctor_name": "d.doctor_name", "specialization": "d.specialization", "department_name": "dep.department_name"},
        "search": ["UPPER(d.doctor_name) LIKE :q", "UPPER(d.specialization) LIKE :q", "UPPER(d.phone) LIKE :q", "UPPER(d.email) LIKE :q", "UPPER(dep.department_name) LIKE :q"],
        "filters": {"department_id": ("d.department_id", "id")},
        "fields": {
            "doctor_name": _field("string", required=True, max_length=150, nullable=False),
            "specialization": _field("string", required=True, max_length=120, nullable=False),
            "phone": _field("phone", max_length=20),
            "email": _field("email", max_length=254),
            "department_id": _field("id", required=True, nullable=False),
        },
    },
    "patients": {
        "table": "Patient", "id": "patient_id", "alias": "p",
        "select": "SELECT p.patient_id AS patient_id, p.patient_name AS patient_name, "
                  "p.date_of_birth AS date_of_birth, p.gender AS gender, p.phone AS phone, "
                  "p.address AS address, p.blood_group AS blood_group FROM Patient p",
        "order": "p.patient_name, p.patient_id",
        "sorts": {"patient_name": "p.patient_name", "date_of_birth": "p.date_of_birth", "gender": "p.gender"},
        "search": ["UPPER(p.patient_name) LIKE :q", "UPPER(p.phone) LIKE :q", "TO_CHAR(p.patient_id) LIKE :q"],
        "filters": {"gender": ("p.gender", "gender"), "blood_group": ("p.blood_group", "blood_group")},
        "fields": {
            "patient_name": _field("string", required=True, max_length=150, nullable=False),
            "date_of_birth": _field("date", required=True, nullable=False),
            "gender": _field("choice", required=True, choices=GENDERS, nullable=False),
            "phone": _field("phone", max_length=20),
            "address": _field("string", max_length=300),
            "blood_group": _field("choice", choices=BLOOD_GROUPS),
        },
    },
    "appointments": {
        "table": "Appointment", "id": "appointment_id", "alias": "a",
        "select": "SELECT a.appointment_id AS appointment_id, a.patient_id AS patient_id, "
                  "p.patient_name AS patient_name, a.doctor_id AS doctor_id, "
                  "d.doctor_name AS doctor_name, dep.department_name AS department_name, "
                  "a.appointment_date AS appointment_date, a.appointment_time AS appointment_time, "
                  "a.status AS status FROM Appointment a "
                  "JOIN Patient p ON p.patient_id = a.patient_id "
                  "JOIN Doctor d ON d.doctor_id = a.doctor_id "
                  "JOIN Department dep ON dep.department_id = d.department_id",
        "order": "a.appointment_date DESC, a.appointment_time, a.appointment_id",
        "sorts": {"appointment_date": "a.appointment_date", "appointment_time": "a.appointment_time", "patient_name": "p.patient_name", "doctor_name": "d.doctor_name", "status": "a.status"},
        "search": ["UPPER(p.patient_name) LIKE :q", "UPPER(d.doctor_name) LIKE :q", "TO_CHAR(a.appointment_id) LIKE :q"],
        "filters": {"patient_id": ("a.patient_id", "id"), "doctor_id": ("a.doctor_id", "id"), "status": ("a.status", "appointment_status")},
        "date_column": "a.appointment_date",
        "fields": {
            "patient_id": _field("id", required=True, nullable=False),
            "doctor_id": _field("id", required=True, nullable=False),
            "appointment_date": _field("date", required=True, nullable=False),
            "appointment_time": _field("time", required=True, nullable=False),
            "status": _field("choice", required=True, choices=APPOINTMENT_STATUSES, default="Scheduled", nullable=False),
        },
    },
    "rooms": {
        "table": "Room", "id": "room_id", "alias": "r",
        "select": "SELECT r.room_id AS room_id, r.room_number AS room_number, "
                  "r.room_type AS room_type, r.availability_status AS availability_status "
                  "FROM Room r",
        "order": "r.room_number, r.room_id",
        "sorts": {"room_number": "r.room_number", "room_type": "r.room_type", "availability_status": "r.availability_status"},
        "search": ["UPPER(r.room_number) LIKE :q", "UPPER(r.room_type) LIKE :q"],
        "filters": {"availability_status": ("r.availability_status", "room_status")},
        "fields": {
            "room_number": _field("string", required=True, max_length=20, nullable=False),
            "room_type": _field("string", required=True, max_length=40, nullable=False),
            "availability_status": _field("choice", choices=ROOM_STATUSES, default="Available", nullable=False),
        },
    },
    "admissions": {
        "table": "Admission", "id": "admission_id", "alias": "a",
        "select": "SELECT a.admission_id AS admission_id, a.patient_id AS patient_id, "
                  "p.patient_name AS patient_name, a.room_id AS room_id, r.room_number AS room_number, "
                  "a.admission_date AS admission_date, a.discharge_date AS discharge_date "
                  "FROM Admission a JOIN Patient p ON p.patient_id = a.patient_id "
                  "JOIN Room r ON r.room_id = a.room_id",
        "order": "a.discharge_date NULLS FIRST, a.admission_date DESC, a.admission_id",
        "sorts": {"admission_date": "a.admission_date", "discharge_date": "a.discharge_date", "patient_name": "p.patient_name", "room_number": "r.room_number"},
        "search": ["UPPER(p.patient_name) LIKE :q", "UPPER(r.room_number) LIKE :q", "TO_CHAR(a.admission_id) LIKE :q"],
        "filters": {"patient_id": ("a.patient_id", "id"), "room_id": ("a.room_id", "id")},
        "date_column": "a.admission_date",
        "fields": {
            "patient_id": _field("id", required=True, nullable=False),
            "room_id": _field("id", required=True, nullable=False),
            "admission_date": _field("date", required=True, nullable=False),
            "discharge_date": _field("date"),
        },
    },
    "medicines": {
        "table": "Medicine", "id": "medicine_id", "alias": "m",
        "select": "SELECT m.medicine_id AS medicine_id, m.medicine_name AS medicine_name, "
                  "m.manufacturer AS manufacturer, m.price AS price, "
                  "m.stock_quantity AS stock_quantity FROM Medicine m",
        "order": "m.medicine_name, m.medicine_id",
        "sorts": {"medicine_name": "m.medicine_name", "price": "m.price", "stock_quantity": "m.stock_quantity"},
        "search": ["UPPER(m.medicine_name) LIKE :q", "UPPER(m.manufacturer) LIKE :q"],
        "filters": {"low_stock": ("m.stock_quantity", "low_stock")},
        "fields": {
            "medicine_name": _field("string", required=True, max_length=150, nullable=False),
            "manufacturer": _field("string", max_length=150),
            "price": _field("money", required=True, default=0, nullable=False),
            "stock_quantity": _field("quantity", required=True, default=0, nullable=False),
        },
    },
    "prescriptions": {
        "table": "Prescription", "id": "prescription_id", "alias": "rx",
        "select": "SELECT rx.prescription_id AS prescription_id, rx.patient_id AS patient_id, "
                  "p.patient_name AS patient_name, rx.doctor_id AS doctor_id, "
                  "d.doctor_name AS doctor_name, rx.medicine_id AS medicine_id, "
                  "m.medicine_name AS medicine_name, rx.dosage AS dosage, rx.duration AS duration, "
                  "rx.prescription_date AS prescription_date FROM Prescription rx "
                  "JOIN Patient p ON p.patient_id = rx.patient_id "
                  "JOIN Doctor d ON d.doctor_id = rx.doctor_id "
                  "JOIN Medicine m ON m.medicine_id = rx.medicine_id",
        "order": "rx.prescription_date DESC, rx.prescription_id DESC",
        "sorts": {"prescription_date": "rx.prescription_date", "patient_name": "p.patient_name", "doctor_name": "d.doctor_name", "medicine_name": "m.medicine_name"},
        "search": ["UPPER(p.patient_name) LIKE :q", "UPPER(d.doctor_name) LIKE :q", "UPPER(m.medicine_name) LIKE :q"],
        "filters": {
            "patient_id": ("rx.patient_id", "id"),
            "doctor_id": ("rx.doctor_id", "id"),
            "medicine_id": ("rx.medicine_id", "id"),
        },
        "date_column": "rx.prescription_date",
        "fields": {
            "patient_id": _field("id", required=True, nullable=False),
            "doctor_id": _field("id", required=True, nullable=False),
            "medicine_id": _field("id", required=True, nullable=False),
            "dosage": _field("string", required=True, max_length=200, nullable=False),
            "duration": _field("string", required=True, max_length=100, nullable=False),
            "prescription_date": _field("date", required=True, nullable=False),
        },
    },
    "bills": {
        "table": "Bill", "id": "bill_id", "alias": "b",
        "select": "SELECT b.bill_id AS bill_id, b.patient_id AS patient_id, "
                  "p.patient_name AS patient_name, b.bill_date AS bill_date, "
                  "b.consultation_charge AS consultation_charge, b.room_charge AS room_charge, "
                  "b.medicine_charge AS medicine_charge, b.total_amount AS total_amount, "
                  "b.payment_status AS payment_status FROM Bill b "
                  "JOIN Patient p ON p.patient_id = b.patient_id",
        "order": "b.bill_date DESC, b.bill_id DESC",
        "sorts": {"bill_date": "b.bill_date", "patient_name": "p.patient_name", "total_amount": "b.total_amount", "payment_status": "b.payment_status"},
        "search": ["UPPER(p.patient_name) LIKE :q", "TO_CHAR(b.bill_id) LIKE :q"],
        "filters": {"patient_id": ("b.patient_id", "id"), "payment_status": ("b.payment_status", "bill_status")},
        "date_column": "b.bill_date",
        "fields": {
            "patient_id": _field("id", required=True, nullable=False),
            "bill_date": _field("date", required=True, nullable=False),
            "consultation_charge": _field("money", required=True, default=0, nullable=False),
            "room_charge": _field("money", required=True, default=0, nullable=False),
            "medicine_charge": _field("money", required=True, default=0, nullable=False),
            "payment_status": _field("choice", required=True, choices=BILL_STATUSES, default="Pending", nullable=False),
        },
    },
}


REPORTS: dict[str, dict[str, Any]] = {
    "department-doctor-counts": {
        "select": "SELECT dep.department_id AS department_id, dep.department_name AS department_name, "
                  "dep.location AS location, COUNT(d.doctor_id) AS doctor_count "
                  "FROM Department dep LEFT JOIN Doctor d ON d.department_id = dep.department_id",
        "group_by": " GROUP BY dep.department_id, dep.department_name, dep.location",
        "order": "department_name, department_id",
        "filters": {},
    },
    "patient-appointments": {
        "select": "SELECT a.appointment_id AS appointment_id, a.appointment_date AS appointment_date, "
                  "a.appointment_time AS appointment_time, a.status AS status, "
                  "p.patient_id AS patient_id, p.patient_name AS patient_name, "
                  "d.doctor_id AS doctor_id, d.doctor_name AS doctor_name, "
                  "dep.department_name AS department_name FROM Appointment a "
                  "JOIN Patient p ON p.patient_id = a.patient_id "
                  "JOIN Doctor d ON d.doctor_id = a.doctor_id "
                  "JOIN Department dep ON dep.department_id = d.department_id",
        "order": "appointment_date DESC, appointment_time, appointment_id",
        "filters": {"patient_id": ("a.patient_id", "id"), "doctor_id": ("a.doctor_id", "id"), "status": ("a.status", "appointment_status")},
        "date_column": "a.appointment_date",
    },
    "doctor-schedule": {
        "select": "SELECT a.appointment_id AS appointment_id, a.appointment_date AS appointment_date, "
                  "a.appointment_time AS appointment_time, p.patient_name AS patient_name, "
                  "d.doctor_id AS doctor_id, d.doctor_name AS doctor_name, "
                  "dep.department_name AS department_name, a.status AS status "
                  "FROM Appointment a JOIN Patient p ON p.patient_id = a.patient_id "
                  "JOIN Doctor d ON d.doctor_id = a.doctor_id "
                  "JOIN Department dep ON dep.department_id = d.department_id",
        "base_where": ["a.status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation')", "a.appointment_date >= TRUNC(SYSDATE)"],
        "order": "appointment_date, appointment_time, doctor_name",
        "filters": {"doctor_id": ("a.doctor_id", "id")},
        "date_column": "a.appointment_date",
    },
    "appointments-by-date-status": {
        "select": "SELECT TRUNC(a.appointment_date) AS appointment_date, a.status AS status, "
                  "COUNT(*) AS appointment_count FROM Appointment a",
        "group_by": " GROUP BY TRUNC(a.appointment_date), a.status",
        "order": "appointment_date DESC, status",
        "filters": {"status": ("a.status", "appointment_status")},
        "date_column": "a.appointment_date",
    },
    "current-admissions": {
        "select": "SELECT a.admission_id AS admission_id, p.patient_id AS patient_id, "
                  "p.patient_name AS patient_name, r.room_id AS room_id, r.room_number AS room_number, "
                  "r.room_type AS room_type, a.admission_date AS admission_date "
                  "FROM Admission a JOIN Patient p ON p.patient_id = a.patient_id "
                  "JOIN Room r ON r.room_id = a.room_id",
        "base_where": ["a.discharge_date IS NULL"],
        "order": "admission_date DESC, room_number",
        "filters": {"patient_id": ("a.patient_id", "id"), "room_id": ("a.room_id", "id")},
        "date_column": "a.admission_date",
    },
    "admission-history": {
        "select": "SELECT a.admission_id AS admission_id, p.patient_id AS patient_id, "
                  "p.patient_name AS patient_name, r.room_id AS room_id, r.room_number AS room_number, "
                  "a.admission_date AS admission_date, a.discharge_date AS discharge_date "
                  "FROM Admission a JOIN Patient p ON p.patient_id = a.patient_id "
                  "JOIN Room r ON r.room_id = a.room_id",
        "order": "admission_date DESC, admission_id DESC",
        "filters": {"patient_id": ("a.patient_id", "id"), "room_id": ("a.room_id", "id")},
        "date_column": "a.admission_date",
    },
    "room-occupancy": {
        "select": "SELECT r.availability_status AS availability_status, COUNT(*) AS room_count "
                  "FROM Room r",
        "group_by": " GROUP BY r.availability_status",
        "order": "availability_status",
        "filters": {},
    },
    "low-stock-inventory": {
        "select": "SELECT m.medicine_id AS medicine_id, m.medicine_name AS medicine_name, "
                  "m.manufacturer AS manufacturer, m.price AS price, m.stock_quantity AS stock_quantity "
                  "FROM Medicine m",
        "base_where": ["m.stock_quantity < 10"],
        "order": "stock_quantity, medicine_name",
        "filters": {},
    },
    "prescription-history": {
        "select": "SELECT rx.prescription_id AS prescription_id, rx.prescription_date AS prescription_date, "
                  "p.patient_id AS patient_id, p.patient_name AS patient_name, "
                  "d.doctor_id AS doctor_id, d.doctor_name AS doctor_name, "
                  "m.medicine_id AS medicine_id, m.medicine_name AS medicine_name, "
                  "rx.dosage AS dosage, rx.duration AS duration FROM Prescription rx "
                  "JOIN Patient p ON p.patient_id = rx.patient_id "
                  "JOIN Doctor d ON d.doctor_id = rx.doctor_id "
                  "JOIN Medicine m ON m.medicine_id = rx.medicine_id",
        "order": "prescription_date DESC, prescription_id DESC",
        "filters": {
            "patient_id": ("rx.patient_id", "id"), "doctor_id": ("rx.doctor_id", "id"),
            "medicine_id": ("rx.medicine_id", "id"),
        },
        "date_column": "rx.prescription_date",
    },
    "patient-bills": {
        "select": "SELECT b.bill_id AS bill_id, b.bill_date AS bill_date, "
                  "p.patient_id AS patient_id, p.patient_name AS patient_name, "
                  "b.consultation_charge AS consultation_charge, b.room_charge AS room_charge, "
                  "b.medicine_charge AS medicine_charge, b.total_amount AS total_amount, "
                  "b.payment_status AS payment_status FROM Bill b "
                  "JOIN Patient p ON p.patient_id = b.patient_id",
        "order": "bill_date DESC, bill_id DESC",
        "filters": {"patient_id": ("b.patient_id", "id"), "payment_status": ("b.payment_status", "bill_status")},
        "date_column": "b.bill_date",
    },
    "billing-by-status": {
        "select": "SELECT b.payment_status AS payment_status, COUNT(*) AS bill_count, "
                  "NVL(SUM(b.total_amount), 0) AS total_amount FROM Bill b",
        "group_by": " GROUP BY b.payment_status",
        "order": "payment_status",
        "filters": {},
    },
    "monthly-revenue": {
        "select": "SELECT TRUNC(b.bill_date, 'MM') AS revenue_month, "
                  "SUM(CASE WHEN b.payment_status = 'Paid' THEN b.total_amount ELSE 0 END) AS collected_total, "
                  "SUM(CASE WHEN b.payment_status = 'Pending' THEN b.total_amount ELSE 0 END) AS outstanding_total "
                  "FROM Bill b",
        "group_by": " GROUP BY TRUNC(b.bill_date, 'MM')",
        "order": "revenue_month DESC",
        "filters": {},
        "date_column": "b.bill_date",
    },
}


@api.errorhandler(ApiError)
def handle_api_error(error: ApiError):
    return jsonify({"error": {"code": error.code, "message": error.message}}), error.status


@api.get("/api/health")
def health():
    db = _db()
    with db.connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok FROM dual")
            cursor.fetchone()
    return jsonify({"data": {"status": "ok", "database": "oracle"}})


@api.get("/api/dashboard")
def dashboard():
    with _db().connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT "
                "(SELECT COUNT(*) FROM Patient) AS patients, "
                "(SELECT COUNT(*) FROM Doctor) AS doctors, "
                "(SELECT COUNT(*) FROM Department) AS departments, "
                "(SELECT COUNT(*) FROM Appointment) AS appointments, "
                "(SELECT COUNT(*) FROM Appointment WHERE status = 'Scheduled' "
                " AND appointment_date >= TRUNC(SYSDATE)) AS upcoming_appointments, "
                "(SELECT COUNT(*) FROM Appointment WHERE appointment_date = TRUNC(SYSDATE) "
                " AND status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation')) AS today_queue_appointments, "
                "(SELECT COUNT(*) FROM Appointment WHERE status = 'Completed') AS completed_appointments, "
                "(SELECT COUNT(*) FROM Appointment WHERE status = 'Cancelled') AS cancelled_appointments, "
                "(SELECT COUNT(*) FROM Admission WHERE discharge_date IS NULL) AS active_admissions, "
                "(SELECT COUNT(*) FROM Room) AS total_rooms, "
                "(SELECT COUNT(*) FROM Room WHERE availability_status = 'Available') AS available_rooms, "
                "(SELECT COUNT(*) FROM Room WHERE availability_status = 'Occupied') AS occupied_rooms, "
                "(SELECT COUNT(*) FROM Room WHERE availability_status = 'Maintenance') AS maintenance_rooms, "
                "(SELECT COUNT(*) FROM Medicine) AS total_medicines, "
                "(SELECT COUNT(*) FROM Medicine WHERE stock_quantity < 10) AS low_stock_medicines, "
                "(SELECT COUNT(*) FROM Bill WHERE payment_status = 'Pending') AS pending_bills, "
                "(SELECT COUNT(*) FROM Bill WHERE payment_status = 'Paid') AS paid_bills, "
                "NVL((SELECT SUM(total_amount) FROM Bill WHERE payment_status = 'Pending'), 0) AS outstanding_total, "
                "NVL((SELECT SUM(total_amount) FROM Bill WHERE payment_status = 'Paid'), 0) AS collected_total "
                "FROM dual"
            )
            names = [column[0].lower() for column in cursor.description]
            values = cursor.fetchone()
            summary = dict(zip(names, values))
            count_keys = set(names) - {"outstanding_total", "collected_total"}
            counts = {key: int(summary[key]) for key in count_keys}

            cursor.execute(
                "SELECT a.appointment_id AS appointment_id, p.patient_name AS patient_name, "
                "d.doctor_name AS doctor_name, a.appointment_date AS appointment_date, "
                "a.appointment_time AS appointment_time, a.status AS status "
                "FROM Appointment a JOIN Patient p ON p.patient_id = a.patient_id "
                "JOIN Doctor d ON d.doctor_id = a.doctor_id "
                "WHERE a.status = 'Scheduled' AND a.appointment_date >= TRUNC(SYSDATE) "
                "ORDER BY a.appointment_date, a.appointment_time FETCH FIRST 8 ROWS ONLY"
            )
            upcoming = _fetch_rows(cursor)

            cursor.execute(
                "SELECT b.bill_id AS bill_id, p.patient_name AS patient_name, "
                "b.bill_date AS bill_date, b.total_amount AS total_amount "
                "FROM Bill b JOIN Patient p ON p.patient_id = b.patient_id "
                "WHERE b.payment_status = 'Pending' "
                "ORDER BY b.bill_date, b.bill_id FETCH FIRST 6 ROWS ONLY"
            )
            outstanding = _fetch_rows(cursor)

            cursor.execute(
                "SELECT activity_type, record_id, description, record_date, resource "
                "FROM ("
                "  SELECT 'Appointment' AS activity_type, a.appointment_id AS record_id, "
                "         p.patient_name || ' · ' || d.doctor_name AS description, "
                "         a.appointment_date AS record_date, 'appointments' AS resource "
                "    FROM Appointment a JOIN Patient p ON p.patient_id = a.patient_id "
                "    JOIN Doctor d ON d.doctor_id = a.doctor_id "
                "  UNION ALL "
                "  SELECT 'Admission', a.admission_id, p.patient_name || ' · ' || r.room_number, "
                "         a.admission_date, 'admissions' "
                "    FROM Admission a JOIN Patient p ON p.patient_id = a.patient_id "
                "    JOIN Room r ON r.room_id = a.room_id "
                "  UNION ALL "
                "  SELECT 'Prescription', rx.prescription_id, p.patient_name || ' · ' || m.medicine_name, "
                "         rx.prescription_date, 'prescriptions' "
                "    FROM Prescription rx JOIN Patient p ON p.patient_id = rx.patient_id "
                "    JOIN Medicine m ON m.medicine_id = rx.medicine_id "
                "  UNION ALL "
                "  SELECT 'Bill', b.bill_id, p.patient_name || ' · ' || b.payment_status, "
                "         b.bill_date, 'bills' "
                "    FROM Bill b JOIN Patient p ON p.patient_id = b.patient_id "
                ") activity ORDER BY record_date DESC, activity_type FETCH FIRST 8 ROWS ONLY"
            )
            recent_records = _fetch_rows(cursor)

            cursor.execute(
                "SELECT medicine_id, medicine_name, manufacturer, stock_quantity "
                "FROM Medicine WHERE stock_quantity < 10 "
                "ORDER BY stock_quantity, medicine_name FETCH FIRST 8 ROWS ONLY"
            )
            low_stock = _fetch_rows(cursor)

    return jsonify({"data": {
        "counts": counts,
        "outstanding_total": _json_value(summary["outstanding_total"]),
        "collected_total": _json_value(summary["collected_total"]),
        "upcoming_appointments": upcoming,
        "outstanding_bills": outstanding,
        "low_stock_medicines": low_stock,
        "recent_records": recent_records,
    }})


@api.get("/api/options")
def options():
    with _db().connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT department_id AS id, department_name AS label FROM Department ORDER BY department_name")
            departments = _fetch_rows(cursor)
            cursor.execute(
                "SELECT d.doctor_id AS id, d.doctor_name AS label, d.department_id AS department_id, "
                "dep.department_name AS department_name FROM Doctor d "
                "JOIN Department dep ON dep.department_id = d.department_id ORDER BY d.doctor_name"
            )
            doctors = _fetch_rows(cursor)
            cursor.execute("SELECT patient_id AS id, patient_name AS label FROM Patient ORDER BY patient_name")
            patients = _fetch_rows(cursor)
            cursor.execute(
                "SELECT room_id AS id, room_number AS label, room_type AS room_type "
                "FROM Room WHERE availability_status = 'Available' ORDER BY room_number"
            )
            available_rooms = _fetch_rows(cursor)
            cursor.execute("SELECT room_id AS id, room_number AS label FROM Room ORDER BY room_number")
            rooms = _fetch_rows(cursor)
            cursor.execute("SELECT medicine_id AS id, medicine_name AS label FROM Medicine ORDER BY medicine_name")
            medicines = _fetch_rows(cursor)
    return jsonify({"data": {
        "departments": departments, "doctors": doctors, "patients": patients,
        "available_rooms": available_rooms, "rooms": rooms, "medicines": medicines,
    }})


@api.get("/api/reports/<string:report_name>")
def report_rows(report_name: str):
    if report_name not in REPORTS:
        raise ApiError("Unknown report.", 404, "not_found")
    with _db().connection() as connection:
        with connection.cursor() as cursor:
            rows, pagination = _list_report(cursor, report_name, request.args)
    return jsonify({"data": rows, "meta": {"pagination": pagination}})


@api.get("/api/reports/<string:report_name>/csv")
def report_csv(report_name: str):
    """Export every row matching the report's validated filters, not just one UI page."""
    if report_name not in REPORTS:
        raise ApiError("Unknown report.", 404, "not_found")
    with _db().connection() as connection:
        with connection.cursor() as cursor:
            query, binds, _filtered_sql = _build_report_query(report_name, request.args)
            cursor.execute(query, binds)
            headers = [column[0].lower() for column in cursor.description]
            rows = cursor.fetchall()

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow([_csv_header(header) for header in headers])
    writer.writerows([_csv_value(value) for value in row] for row in rows)
    response = Response(output.getvalue(), content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{report_name}.csv"'
    response.headers["Cache-Control"] = "no-store"
    return response


@api.get("/api/patients/<int:patient_id>/summary")
def patient_summary(patient_id: int):
    with _db().connection() as connection:
        with connection.cursor() as cursor:
            patient = _fetch_one(cursor, RESOURCES["patients"]["select"] + " WHERE p.patient_id = :record_id", {"record_id": patient_id})
            if patient is None:
                raise ApiError("Patient not found.", 404, "not_found")
            related: dict[str, list[dict[str, Any]]] = {}
            for name in ("appointments", "admissions", "prescriptions", "bills"):
                spec = RESOURCES[name]
                column = {
                    "appointments": "a.patient_id", "admissions": "a.patient_id",
                    "prescriptions": "rx.patient_id", "bills": "b.patient_id",
                }[name]
                cursor.execute(spec["select"] + f" WHERE {column} = :patient_id ORDER BY {spec['order']}", {"patient_id": patient_id})
                related[name] = _fetch_rows(cursor)
    return jsonify({"data": {
        "patient": patient,
        **related,
        "timeline": _patient_timeline(related),
    }})


def _patient_timeline(related: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Combine only stored patient facts into a newest-first administrative timeline."""
    events: list[dict[str, Any]] = []

    def add(record_date: Any, record_time: Any, kind: str, details: str,
            status: str, record_id: Any) -> None:
        if not record_date:
            return
        events.append({
            "date": str(record_date)[:10],
            "time": str(record_time) if record_time else None,
            "type": kind,
            "details": details,
            "status": status,
            "record_id": record_id,
        })

    for row in related.get("appointments", []):
        add(
            row.get("appointment_date"), row.get("appointment_time"), "Appointment",
            " · ".join(part for part in (row.get("doctor_name"), row.get("department_name")) if part),
            str(row.get("status") or "Recorded"), row.get("appointment_id"),
        )

    for row in related.get("admissions", []):
        room = f"Room {row.get('room_number')}" if row.get("room_number") else "Room not recorded"
        active = not row.get("discharge_date")
        admission_id = row.get("admission_id")
        add(row.get("admission_date"), None, "Admission", room,
            "Active stay" if active else "Discharged", admission_id)
        if row.get("discharge_date"):
            add(row.get("discharge_date"), None, "Discharge", room,
                "Room released", admission_id)

    for row in related.get("prescriptions", []):
        details = " · ".join(part for part in (
            row.get("medicine_name"), row.get("dosage"), row.get("duration"),
            row.get("doctor_name"),
        ) if part)
        add(row.get("prescription_date"), None, "Prescription", details,
            "Instruction recorded; dispensing not recorded", row.get("prescription_id"))

    for row in related.get("bills", []):
        total = row.get("total_amount")
        if total is None:
            details = "Bill total not recorded"
        else:
            try:
                details = f"Bill total ₹{Decimal(str(total)):,.2f}"
            except (InvalidOperation, ValueError):
                details = f"Bill total {total}"
        add(row.get("bill_date"), None, "Bill", details,
            str(row.get("payment_status") or "Status not recorded"), row.get("bill_id"))

    events.sort(key=lambda event: (
        event["date"], event["time"] or "", event["type"], str(event["record_id"] or ""),
    ), reverse=True)
    return events


@api.get("/api/appointments/queue")
def appointment_queue():
    """Return one database-backed day's appointments in deterministic queue order."""
    raw_date = request.args.get("date")
    if not raw_date:
        raise ApiError("Queue date is required.")
    queue_date = _validate_date(raw_date, "date")
    binds: dict[str, Any] = {"queue_date": queue_date}
    where = ["a.appointment_date = :queue_date"]
    raw_doctor_id = request.args.get("doctor_id")
    doctor_id = None
    if raw_doctor_id not in (None, ""):
        doctor_id = _parse_integer(raw_doctor_id, "doctor_id", minimum=1, maximum=9_999_999_999)
        where.append("a.doctor_id = :doctor_id")
        binds["doctor_id"] = doctor_id

    where_sql = " AND ".join(where)
    with _db().connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT a.appointment_id AS appointment_id, a.patient_id AS patient_id, "
                "p.patient_name AS patient_name, a.doctor_id AS doctor_id, "
                "d.doctor_name AS doctor_name, dep.department_name AS department_name, "
                "a.appointment_date AS appointment_date, a.appointment_time AS appointment_time, "
                "a.status AS status FROM Appointment a "
                "JOIN Patient p ON p.patient_id = a.patient_id "
                "JOIN Doctor d ON d.doctor_id = a.doctor_id "
                "JOIN Department dep ON dep.department_id = d.department_id "
                f"WHERE {where_sql} "
                "ORDER BY CASE a.status "
                "WHEN 'Waiting' THEN 1 WHEN 'Checked In' THEN 2 WHEN 'Scheduled' THEN 3 "
                "WHEN 'In Consultation' THEN 4 WHEN 'Completed' THEN 5 "
                "WHEN 'No-show' THEN 6 WHEN 'Cancelled' THEN 7 ELSE 8 END, "
                "a.appointment_time, a.appointment_id",
                binds,
            )
            rows = _fetch_rows(cursor)

    counts = {status: 0 for status in APPOINTMENT_STATUSES}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    next_patient = next((
        row for row in rows
        if row["status"] in ("Waiting", "Checked In", "Scheduled")
    ), None)
    return jsonify({"data": {
        "date": queue_date.date().isoformat(),
        "doctor_id": doctor_id,
        "rows": rows,
        "counts": counts,
        "next_patient": next_patient,
    }})


@api.get("/api/details/<string:resource_name>/<int:record_id>")
def resource_details(resource_name: str, record_id: int):
    spec = _resource(resource_name)
    related: dict[str, list[dict[str, Any]]] = {}
    with _db().connection() as connection:
        with connection.cursor() as cursor:
            record = _fetch_one(
                cursor,
                spec["select"] + f" WHERE {spec['alias']}.{spec['id']} = :record_id",
                {"record_id": record_id},
            )
            if record is None:
                raise ApiError("Record not found.", 404, "not_found")

            if resource_name == "departments":
                cursor.execute(
                    RESOURCES["doctors"]["select"] + " WHERE d.department_id = :record_id "
                    "ORDER BY d.doctor_name FETCH FIRST 20 ROWS ONLY",
                    {"record_id": record_id},
                )
                related["doctors"] = _fetch_rows(cursor)
            elif resource_name == "doctors":
                cursor.execute(
                    RESOURCES["appointments"]["select"] + " WHERE a.doctor_id = :record_id "
                    "ORDER BY a.appointment_date DESC, a.appointment_time FETCH FIRST 20 ROWS ONLY",
                    {"record_id": record_id},
                )
                related["appointments"] = _fetch_rows(cursor)
                cursor.execute(
                    RESOURCES["prescriptions"]["select"] + " WHERE rx.doctor_id = :record_id "
                    "ORDER BY rx.prescription_date DESC FETCH FIRST 20 ROWS ONLY",
                    {"record_id": record_id},
                )
                related["prescriptions"] = _fetch_rows(cursor)
            elif resource_name == "rooms":
                cursor.execute(
                    RESOURCES["admissions"]["select"] + " WHERE a.room_id = :record_id "
                    "ORDER BY a.admission_date DESC FETCH FIRST 20 ROWS ONLY",
                    {"record_id": record_id},
                )
                related["admissions"] = _fetch_rows(cursor)
            elif resource_name == "medicines":
                cursor.execute(
                    RESOURCES["prescriptions"]["select"] + " WHERE rx.medicine_id = :record_id "
                    "ORDER BY rx.prescription_date DESC FETCH FIRST 20 ROWS ONLY",
                    {"record_id": record_id},
                )
                related["prescriptions"] = _fetch_rows(cursor)
    return jsonify({"data": {"record": record, "related": related}})


@api.route("/api/<string:resource_name>", methods=["GET", "POST"])

def collection(resource_name: str):
    spec = _resource(resource_name)
    if request.method == "GET":
        with _db().connection() as connection:
            with connection.cursor() as cursor:
                rows, page_info = _list_resource(cursor, resource_name, request.args)
        return jsonify({"data": rows, "meta": {"pagination": page_info}})

    payload = _request_json()
    values = _validate_payload(spec, payload, partial=False)
    if resource_name == "rooms" and values.get("availability_status") == "Occupied":
        raise ApiError("Rooms are marked Occupied when an active admission is created.", 400)
    if resource_name == "appointments":
        if values.get("status") != "Scheduled":
            raise ApiError("New appointments must start as Scheduled; use the appointment workflow for status changes.")
        _validate_scheduled_appointment(values)
    columns = list(values)
    placeholders = [f":{column}" for column in columns]
    sql = f"INSERT INTO {spec['table']} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
    with _transaction(_db()) as connection:
        with connection.cursor() as cursor:
            out_id = cursor.var(int)
            binds = dict(values)
            binds["out_id"] = out_id
            cursor.execute(sql + f" RETURNING {spec['id']} INTO :out_id", binds)
            new_id = _output_value(out_id.getvalue())
    return jsonify({"data": {"id": int(new_id)}}), 201


@api.route("/api/<string:resource_name>/<int:record_id>", methods=["GET", "PUT", "DELETE"])
def record(resource_name: str, record_id: int):
    spec = _resource(resource_name)
    if request.method == "GET":
        with _db().connection() as connection:
            with connection.cursor() as cursor:
                result = _fetch_one(cursor, spec["select"] + f" WHERE {spec['alias']}.{spec['id']} = :record_id", {"record_id": record_id})
        if result is None:
            raise ApiError("Record not found.", 404, "not_found")
        return jsonify({"data": result})

    if request.method == "PUT":
        payload = _request_json()
        values = _validate_payload(spec, payload, partial=True)
        if not values:
            raise ApiError("Provide at least one field to update.")
        if resource_name == "medicines" and "stock_quantity" in values:
            raise ApiError("Use the stock-adjustments action to change inventory safely.")
        if resource_name == "appointments":
            _update_appointment(record_id, values)
        elif resource_name == "rooms":
            _update_room(record_id, values)
        elif resource_name == "admissions":
            if set(values) != {"room_id"}:
                raise ApiError("Only an active admission's room can be changed; use the discharge action for discharge dates.")
            with _transaction(_db()) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE Admission SET room_id = :room_id "
                        "WHERE admission_id = :record_id AND discharge_date IS NULL",
                        {"room_id": values["room_id"], "record_id": record_id},
                    )
                    if cursor.rowcount == 0:
                        cursor.execute("SELECT discharge_date FROM Admission WHERE admission_id = :record_id", {"record_id": record_id})
                        admission = cursor.fetchone()
                        if admission is None:
                            raise ApiError("Admission not found.", 404, "not_found")
                        raise ApiError("A discharged admission is read-only history.", 409, "admission_history")
        else:
            assignments = ", ".join(f"{column} = :{column}" for column in values)
            binds = dict(values)
            binds["record_id"] = record_id
            with _transaction(_db()) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE {spec['table']} SET {assignments} WHERE {spec['id']} = :record_id",
                        binds,
                    )
                    if cursor.rowcount == 0:
                        raise ApiError("Record not found.", 404, "not_found")
        with _db().connection() as connection:
            with connection.cursor() as cursor:
                updated = _fetch_one(cursor, spec["select"] + f" WHERE {spec['alias']}.{spec['id']} = :record_id", {"record_id": record_id})
        return jsonify({"data": updated})

    if resource_name == "appointments":
        raise ApiError(
            "Appointment history is retained. Cancel a scheduled appointment instead of deleting it.",
            409,
            "appointment_history",
        )
    if resource_name == "prescriptions":
        raise ApiError("Prescription history is retained and cannot be deleted.", 409, "prescription_history")
    if resource_name == "bills":
        raise ApiError("Billing history is retained and cannot be deleted.", 409, "billing_history")

    # Admission and appointment records are history; retain them after discharge/cancellation.
    if resource_name == "admissions":
        with _db().connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT discharge_date FROM Admission WHERE admission_id = :record_id", {"record_id": record_id})
                admission = cursor.fetchone()
        if admission is None:
            raise ApiError("Admission not found.", 404, "not_found")
        if admission[0] is None:
            raise ApiError("Discharge the patient before deleting an active admission.", 409, "active_admission")
        raise ApiError("Admission history is retained and cannot be deleted.", 409, "admission_history")

    # Deletion of unreferenced master/data rows is still restricted by Oracle foreign keys.
    with _transaction(_db()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {spec['table']} WHERE {spec['id']} = :record_id", {"record_id": record_id})
            if cursor.rowcount == 0:
                raise ApiError("Record not found.", 404, "not_found")
    return jsonify({"data": {"deleted": True, "id": record_id}})


@api.post("/api/medicines/<int:medicine_id>/stock-adjustments")
def adjust_medicine_stock(medicine_id: int):
    payload = _request_json()
    if set(payload) != {"change"}:
        raise ApiError("Supply one integer 'change' value; positive adds stock and negative removes it.")
    change = _parse_integer(payload["change"], "change", minimum=-9_999_999_999, maximum=9_999_999_999)
    if change == 0:
        raise ApiError("Stock change cannot be zero.")
    # One conditional UPDATE is atomic and row-locked by Oracle. The CHECK constraint
    # remains the final guard. Prescriptions intentionally do not consume stock.
    with _transaction(_db()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE Medicine SET stock_quantity = stock_quantity + :change "
                "WHERE medicine_id = :medicine_id "
                "AND stock_quantity + :change BETWEEN 0 AND 9999999999",
                {"change": change, "medicine_id": medicine_id},
            )
            if cursor.rowcount == 0:
                cursor.execute("SELECT stock_quantity FROM Medicine WHERE medicine_id = :medicine_id", {"medicine_id": medicine_id})
                row = cursor.fetchone()
                if row is None:
                    raise ApiError("Medicine not found.", 404, "not_found")
                if int(row[0]) + change < 0:
                    raise ApiError("Stock cannot be reduced below zero.", 409, "insufficient_stock")
                raise ApiError("The resulting stock exceeds the supported quantity.", 409, "stock_limit")
            cursor.execute("SELECT stock_quantity FROM Medicine WHERE medicine_id = :medicine_id", {"medicine_id": medicine_id})
            new_stock = cursor.fetchone()[0]
    return jsonify({"data": {"medicine_id": medicine_id, "stock_quantity": int(new_stock)}})


@api.post("/api/admissions/<int:admission_id>/discharge")
def discharge_admission(admission_id: int):
    payload = _request_json()
    if set(payload) != {"discharge_date"}:
        raise ApiError("Supply only the discharge_date field.")
    discharge = _validate_date(payload.get("discharge_date"), "discharge_date")
    if discharge.date() > date.today():
        raise ApiError("Discharge date cannot be in the future.")
    with _transaction(_db()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE Admission SET discharge_date = :discharge_date "
                "WHERE admission_id = :admission_id AND discharge_date IS NULL",
                {"discharge_date": discharge, "admission_id": admission_id},
            )
            if cursor.rowcount == 0:
                cursor.execute("SELECT discharge_date FROM Admission WHERE admission_id = :admission_id", {"admission_id": admission_id})
                row = cursor.fetchone()
                if row is None:
                    raise ApiError("Admission not found.", 404, "not_found")
                raise ApiError("This admission has already been discharged.", 409, "already_discharged")
    return jsonify({"data": {"admission_id": admission_id, "discharge_date": discharge.date().isoformat()}})


def _db():
    return current_app.extensions["hms_database"]


@contextmanager
def _transaction(database):
    with database.connection() as connection:
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def _resource(name: str) -> dict[str, Any]:
    try:
        return RESOURCES[name]
    except KeyError as exc:
        raise ApiError("Unknown resource.", 404, "not_found") from exc


def _request_json() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ApiError("Request body must be a JSON object.")
    return payload


def _validate_payload(spec: dict[str, Any], payload: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    fields = spec["fields"]
    unknown = set(payload) - set(fields)
    if unknown:
        raise ApiError(f"Unsupported field: {sorted(unknown)[0]}.")
    cleaned: dict[str, Any] = {}
    for name, definition in fields.items():
        if name not in payload:
            if partial:
                continue
            if definition["default"] is not None:
                cleaned[name] = _cast_value(definition, definition["default"], name)
                continue
            if definition["required"]:
                raise ApiError(f"{_label(name)} is required.")
            continue
        raw = payload[name]
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            if definition["required"] or not definition["nullable"]:
                raise ApiError(f"{_label(name)} is required.")
            cleaned[name] = None
            continue
        cleaned[name] = _cast_value(definition, raw, name)
    return cleaned


def _cast_value(definition: dict[str, Any], raw: Any, name: str) -> Any:
    kind = definition["type"]
    if kind in ("string", "phone", "email", "choice"):
        if not isinstance(raw, str):
            raise ApiError(f"{_label(name)} must be text.")
        value = raw.strip()
        if not value:
            if definition["required"] or not definition["nullable"]:
                raise ApiError(f"{_label(name)} is required.")
            return None
        maximum = definition["max_length"]
        if maximum and len(value) > maximum:
            raise ApiError(f"{_label(name)} must be at most {maximum} characters.")
        if kind == "choice" and value not in definition["choices"]:
            choices = ", ".join(definition["choices"])
            raise ApiError(f"{_label(name)} must be one of: {choices}.")
        if kind == "phone" and (
            not re.fullmatch(r"[+0-9() .-]{5,20}", value)
            or sum(character.isdigit() for character in value) < 5
        ):
            raise ApiError("Phone must contain at least five digits and only common phone punctuation.")
        if kind == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ApiError("Enter a valid email address.")
        return value
    if kind == "id":
        return _parse_integer(raw, _label(name), minimum=1, maximum=9_999_999_999)
    if kind == "quantity":
        return _parse_integer(raw, _label(name), minimum=0, maximum=9_999_999_999)
    if kind == "money":
        try:
            value = Decimal(str(raw))
            if not value.is_finite():
                raise InvalidOperation
            rounded = value.quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise ApiError(f"{_label(name)} must be a valid amount.") from None
        if rounded != value or value < 0:
            raise ApiError(f"{_label(name)} must be non-negative with at most two decimal places.")
        if value > Decimal("99999999.99"):
            raise ApiError(f"{_label(name)} exceeds the supported amount.")
        return value
    if kind == "date":
        value = _validate_date(raw, _label(name))
        if name == "date_of_birth" and value.date() > date.today():
            raise ApiError("Date of birth cannot be in the future.")
        if name == "admission_date" and value.date() > date.today():
            raise ApiError("Admission date cannot be in the future.")
        if name == "prescription_date" and value.date() > date.today():
            raise ApiError("Prescription date cannot be in the future.")
        return value
    if kind == "time":
        if not isinstance(raw, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", raw.strip()):
            raise ApiError("Appointment time must use 24-hour HH:MM format.")
        return raw.strip()
    raise ApiError("Unsupported field type in server configuration.", 500, "server_error")


def _validate_scheduled_appointment(values: dict[str, Any]) -> None:
    if values.get("status", "Scheduled") != "Scheduled":
        return
    if "appointment_date" not in values:
        raise ApiError("Appointment date is required.")
    if values["appointment_date"].date() < date.today():
        raise ApiError("A scheduled appointment must not be in the past.")


def _update_appointment(appointment_id: int, values: dict[str, Any]) -> None:
    """Lock the row, validate its state transition, then update atomically."""
    booking_fields = {"patient_id", "doctor_id", "appointment_date", "appointment_time"}
    terminal_statuses = {"Completed", "Cancelled", "No-show"}
    with _transaction(_db()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT patient_id, doctor_id, appointment_date, appointment_time, status "
                "FROM Appointment WHERE appointment_id = :appointment_id FOR UPDATE",
                {"appointment_id": appointment_id},
            )
            current = cursor.fetchone()
            if current is None:
                raise ApiError("Appointment not found.", 404, "not_found")

            columns = ("patient_id", "doctor_id", "appointment_date", "appointment_time", "status")
            current_values = dict(zip(columns, current))
            changed_fields = {
                key for key in columns
                if key in values and values[key] != current_values[key]
            }
            current_status = current_values["status"]
            effective_status = values.get("status", current_status)
            effective_date = values.get("appointment_date", current_values["appointment_date"])
            effective_day = effective_date.date() if isinstance(effective_date, datetime) else effective_date
            booking_changes = changed_fields & booking_fields
            status_changed = effective_status != current_status

            if current_status in terminal_statuses and changed_fields:
                raise ApiError(
                    "Completed, cancelled, and no-show appointments are read-only history.",
                    409,
                    "appointment_history",
                )
            if booking_changes and current_status != "Scheduled":
                raise ApiError(
                    "Only a scheduled appointment can be rescheduled.",
                    409,
                    "appointment_history",
                )
            if status_changed and booking_changes:
                raise ApiError("Change booking details and appointment status in separate steps.", 409, "invalid_status_transition")
            if status_changed and effective_status not in APPOINTMENT_TRANSITIONS[current_status]:
                raise ApiError(
                    f"Invalid appointment transition from {current_status} to {effective_status}.",
                    409,
                    "invalid_status_transition",
                )

            cursor.execute("SELECT TRUNC(SYSDATE) FROM dual")
            database_today_value = cursor.fetchone()[0]
            database_today = (
                database_today_value.date()
                if isinstance(database_today_value, datetime)
                else database_today_value
            )
            if effective_status == "Scheduled" and effective_day < database_today:
                raise ApiError("A scheduled appointment must not be in the past.")
            if status_changed and effective_status == "Checked In" and effective_day != database_today:
                raise ApiError("Patients can be checked in only on the appointment date.", 409, "appointment_not_today")
            if status_changed and effective_status == "No-show" and effective_day >= database_today:
                raise ApiError("An appointment can be marked No-show only after its date has passed.", 409, "appointment_not_overdue")

            assignments = ", ".join(f"{column} = :{column}" for column in values)
            binds = {**values, "appointment_id": appointment_id}
            cursor.execute(
                f"UPDATE Appointment SET {assignments} WHERE appointment_id = :appointment_id",
                binds,
            )


def _validate_date(raw: Any, label: str) -> datetime:
    if isinstance(raw, datetime):
        return datetime.combine(raw.date(), time.min)
    if isinstance(raw, date):
        return datetime.combine(raw, time.min)
    if not isinstance(raw, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw.strip()):
        raise ApiError(f"{label} must use YYYY-MM-DD format.")
    try:
        parsed = date.fromisoformat(raw.strip())
    except ValueError:
        raise ApiError(f"{label} must use YYYY-MM-DD format.") from None
    return datetime.combine(parsed, time.min)


def _parse_integer(raw: Any, label: str, minimum: int | None = None,
                   maximum: int | None = None) -> int:
    if isinstance(raw, bool):
        raise ApiError(f"{label} must be an integer.")
    if isinstance(raw, int):
        value = raw
    elif isinstance(raw, str) and re.fullmatch(r"-?\d+", raw.strip()):
        value = int(raw.strip())
    else:
        raise ApiError(f"{label} must be an integer.")
    if minimum is not None and value < minimum:
        raise ApiError(f"{label} must be at least {minimum}.")
    if maximum is not None and value > maximum:
        raise ApiError(f"{label} must not exceed {maximum}.")
    return value


def _validate_discharge_date(admission_id: int, discharge_date: datetime) -> None:
    with _db().connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT admission_date FROM Admission WHERE admission_id = :admission_id", {"admission_id": admission_id})
            row = cursor.fetchone()
    if row is None:
        raise ApiError("Admission not found.", 404, "not_found")
    if discharge_date < row[0]:
        raise ApiError("Discharge date cannot be earlier than admission date.")


def _update_room(room_id: int, values: dict[str, Any]) -> None:
    with _transaction(_db()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT availability_status FROM Room WHERE room_id = :room_id FOR UPDATE", {"room_id": room_id})
            room = cursor.fetchone()
            if room is None:
                raise ApiError("Room not found.", 404, "not_found")
            if "availability_status" in values:
                cursor.execute(
                    "SELECT COUNT(*) FROM Admission WHERE room_id = :room_id AND discharge_date IS NULL",
                    {"room_id": room_id},
                )
                has_active_admission = cursor.fetchone()[0] > 0
                requested = values["availability_status"]
                if has_active_admission and requested != "Occupied":
                    raise ApiError("A room with an active admission must remain Occupied until discharge.", 409, "room_in_use")
                if not has_active_admission and requested == "Occupied":
                    raise ApiError("Create an admission to mark a room Occupied.", 409, "room_occupancy_managed")
            assignments = ", ".join(f"{column} = :{column}" for column in values)
            binds = dict(values)
            binds["room_id"] = room_id
            cursor.execute(f"UPDATE Room SET {assignments} WHERE room_id = :room_id", binds)


def _build_report_query(name: str, args: Any) -> tuple[str, dict[str, Any], str]:
    """Build the shared, allowlisted filtered query used by page and CSV exports."""
    spec = REPORTS[name]
    where = list(spec.get("base_where", []))
    binds: dict[str, Any] = {}
    filter_choices = {
        "appointment_status": APPOINTMENT_STATUSES,
        "bill_status": BILL_STATUSES,
    }
    for filter_name, (column, kind) in spec.get("filters", {}).items():
        raw = args.get(filter_name)
        if raw is None or raw == "":
            continue
        if kind == "id":
            binds[f"filter_{filter_name}"] = _parse_integer(raw, filter_name, minimum=1, maximum=9_999_999_999)
        else:
            if raw not in filter_choices[kind]:
                raise ApiError(f"Invalid {filter_name} filter.")
            binds[f"filter_{filter_name}"] = raw
        where.append(f"{column} = :filter_{filter_name}")

    date_bounds: dict[str, date] = {}
    if "date_column" in spec:
        for argument, operator in (("date_from", ">="), ("date_to", "<")):
            raw = args.get(argument)
            if raw:
                parsed_date = _validate_date(raw, argument)
                date_bounds[argument] = parsed_date.date()
                binds[argument] = parsed_date + timedelta(days=1) if argument == "date_to" else parsed_date
                where.append(f"{spec['date_column']} {operator} :{argument}")
        if len(date_bounds) == 2 and date_bounds["date_from"] > date_bounds["date_to"]:
            raise ApiError("date_from must be on or before date_to.")

    where_sql = " WHERE " + " AND ".join(where) if where else ""
    filtered_sql = spec["select"] + where_sql + spec.get("group_by", "")
    query = filtered_sql + " ORDER BY " + spec["order"]
    return query, binds, filtered_sql


def _list_report(cursor: Any, name: str, args: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    query, binds, filtered_sql = _build_report_query(name, args)
    page = _parse_integer(args.get("page", "1"), "page", minimum=1, maximum=1_000_000)
    page_size = _parse_integer(args.get("page_size", "25"), "page_size", minimum=1, maximum=100)
    cursor.execute(f"SELECT COUNT(*) FROM ({filtered_sql}) report_count", binds)
    total = int(cursor.fetchone()[0])
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    page_binds = {**binds, "page_offset": (page - 1) * page_size, "page_size": page_size}
    cursor.execute(
        query + " OFFSET :page_offset ROWS FETCH NEXT :page_size ROWS ONLY",
        page_binds,
    )
    return _fetch_rows(cursor), {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


def _csv_header(name: str) -> str:
    return name.replace("_", " ").title()


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        text = value.date().isoformat() if value.time() == time.min else value.isoformat(timespec="seconds")
    elif isinstance(value, date):
        text = value.isoformat()
    elif isinstance(value, Decimal):
        text = format(value, "f")
    else:
        text = str(value)
    if isinstance(value, str):
        formula_prefix = text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@"))
        control_prefix = text.startswith(("\t", "\r", "\n"))
        if formula_prefix or control_prefix:
            return "'" + text
    return text


def _list_resource(cursor: Any, name: str, args: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    spec = RESOURCES[name]
    where: list[str] = []
    binds: dict[str, Any] = {}
    query = (args.get("q") or "").strip()
    if query:
        if len(query) > 100:
            raise ApiError("Search text must be at most 100 characters.")
        where.append("(" + " OR ".join(spec["search"]) + ")")
        binds["q"] = f"%{query.upper()}%"

    filter_choices = {
        "gender": GENDERS,
        "blood_group": BLOOD_GROUPS,
        "appointment_status": APPOINTMENT_STATUSES,
        "room_status": ROOM_STATUSES,
        "bill_status": BILL_STATUSES,
    }
    for name_key, (column, kind) in spec["filters"].items():
        raw = args.get(name_key)
        if raw is None or raw == "":
            continue
        if kind == "id":
            binds[f"filter_{name_key}"] = _parse_integer(raw, name_key, minimum=1, maximum=9_999_999_999)
            where.append(f"{column} = :filter_{name_key}")
        elif kind == "low_stock":
            if raw not in ("true", "false"):
                raise ApiError("low_stock must be true or false.")
            where.append(f"{column} {'<' if raw == 'true' else '>='} 10")
        else:
            if raw not in filter_choices[kind]:
                raise ApiError(f"Invalid {name_key} filter.")
            binds[f"filter_{name_key}"] = raw
            where.append(f"{column} = :filter_{name_key}")

    date_bounds: dict[str, date] = {}
    if "date_column" in spec:
        for argument, operator in (("date_from", ">="), ("date_to", "<")):
            raw = args.get(argument)
            if raw:
                parsed_date = _validate_date(raw, argument)
                date_bounds[argument] = parsed_date.date()
                binds[argument] = parsed_date + timedelta(days=1) if argument == "date_to" else parsed_date
                where.append(f"{spec['date_column']} {operator} :{argument}")
        if len(date_bounds) == 2 and date_bounds["date_from"] > date_bounds["date_to"]:
            raise ApiError("date_from must be on or before date_to.")

    if name == "admissions" and args.get("active") in ("true", "false"):
        where.append("a.discharge_date IS NULL" if args.get("active") == "true" else "a.discharge_date IS NOT NULL")
    elif name == "admissions" and args.get("active") not in (None, ""):
        raise ApiError("active must be true or false.")

    sort = args.get("sort")
    sort_column = spec["sorts"].get(sort, spec["order"]) if sort else spec["order"]
    direction = (args.get("direction") or "asc").lower()
    if direction not in ("asc", "desc"):
        raise ApiError("direction must be asc or desc.")
    order = sort_column if sort_column == spec["order"] else f"{sort_column} {direction.upper()}"

    page = _parse_integer(args.get("page", "1"), "page", minimum=1, maximum=1_000_000)
    page_size = _parse_integer(args.get("page_size", "25"), "page_size", minimum=1, maximum=100)
    sql = spec["select"]
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    # Reuse the allowlisted FROM/JOIN clause for an efficient count without
    # repeating expensive projection expressions such as department LISTAGG.
    _, separator, from_clause = spec["select"].rpartition(" FROM ")
    if not separator:
        raise RuntimeError(f"Resource {name!r} has no static FROM clause.")
    cursor.execute("SELECT COUNT(*) FROM " + from_clause + where_sql, binds)
    total = int(cursor.fetchone()[0])
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    page_binds = {**binds, "page_offset": (page - 1) * page_size, "page_size": page_size}
    cursor.execute(
        sql + where_sql + " ORDER BY " + order
        + " OFFSET :page_offset ROWS FETCH NEXT :page_size ROWS ONLY",
        page_binds,
    )
    rows = _fetch_rows(cursor)
    return rows, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


def _fetch_rows(cursor: Any) -> list[dict[str, Any]]:
    names = [description[0].lower() for description in cursor.description]
    return [
        {name: _json_value(value) for name, value in zip(names, row)}
        for row in cursor.fetchall()
    ]


def _fetch_one(cursor: Any, sql: str, binds: dict[str, Any] | None = None) -> dict[str, Any] | None:
    cursor.execute(sql, binds or {})
    row = cursor.fetchone()
    if row is None:
        return None
    names = [description[0].lower() for description in cursor.description]
    return {name: _json_value(value) for name, value in zip(names, row)}


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time.min else value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _output_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def _label(name: str) -> str:
    return name.replace("_", " ").capitalize()
