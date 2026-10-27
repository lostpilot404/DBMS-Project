"""API and validation regression tests; no Oracle service is required."""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from hms import create_app
from hms.api import ApiError, APPOINTMENT_STATUSES, RESOURCES, _csv_value, _patient_timeline, _validate_payload
from hms.database import OracleDatabase


class FakeOracleError(Exception):
    pass


class FakeVariable:
    def __init__(self):
        self.value = None

    def getvalue(self):
        return self.value

    def setvalue(self, _position, value):
        self.value = value


class FakeCursor:
    def __init__(self, database):
        self.database = database
        self.description = None
        self.rowcount = -1
        self._one = None
        self._many = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def close(self):
        self.closed = True

    def var(self, _kind):
        return FakeVariable()

    def execute(self, sql, binds=None):
        binds = binds or {}
        self.database.calls.append((sql, binds))
        if self.database.execute_error:
            raise self.database.execute_error
        normalized = " ".join(sql.upper().split())
        if "RETURNING" in normalized and "out_id" in binds:
            binds["out_id"].setvalue(0, self.database.returning_id)
            self.rowcount = 1
        elif normalized.startswith("SELECT 1 AS OK FROM DUAL"):
            self.description = [("OK",)]
            self._one = (1,)
        elif normalized.startswith("SELECT TRUNC(SYSDATE) FROM DUAL"):
            self.description = [("TRUNC(SYSDATE)",)]
            self._one = (self.database.database_today,)
        elif normalized.startswith("SELECT PATIENT_ID, DOCTOR_ID, APPOINTMENT_DATE, APPOINTMENT_TIME, STATUS FROM APPOINTMENT WHERE APPOINTMENT_ID"):
            self.description = [(name,) for name in ("PATIENT_ID", "DOCTOR_ID", "APPOINTMENT_DATE", "APPOINTMENT_TIME", "STATUS")]
            self._one = self.database.appointment_row
        elif "ORDER BY CASE A.STATUS" in normalized and "FROM APPOINTMENT A" in normalized:
            self.description = [(name,) for name in (
                "APPOINTMENT_ID", "PATIENT_ID", "PATIENT_NAME", "DOCTOR_ID", "DOCTOR_NAME",
                "DEPARTMENT_NAME", "APPOINTMENT_DATE", "APPOINTMENT_TIME", "STATUS",
            )]
            self._many = list(self.database.queue_rows)
        elif normalized.startswith("SELECT A.APPOINTMENT_ID AS APPOINTMENT_ID, A.APPOINTMENT_DATE"):
            self.description = [(name,) for name in (
                "APPOINTMENT_ID", "APPOINTMENT_DATE", "APPOINTMENT_TIME", "STATUS", "PATIENT_ID",
                "PATIENT_NAME", "DOCTOR_ID", "DOCTOR_NAME", "DEPARTMENT_NAME",
            )]
            self._many = list(self.database.report_rows)
        elif normalized.startswith("SELECT P.PATIENT_ID AS PATIENT_ID, P.PATIENT_NAME AS PATIENT_NAME"):
            self.description = [(name,) for name in (
                "PATIENT_ID", "PATIENT_NAME", "DATE_OF_BIRTH", "GENDER", "PHONE", "ADDRESS", "BLOOD_GROUP",
            )]
            self._one = self.database.patient_record
        elif "FROM APPOINTMENT A" in normalized and "WHERE A.PATIENT_ID = :PATIENT_ID" in normalized:
            self.description = [(name,) for name in (
                "APPOINTMENT_ID", "PATIENT_ID", "PATIENT_NAME", "DOCTOR_ID", "DOCTOR_NAME",
                "DEPARTMENT_NAME", "APPOINTMENT_DATE", "APPOINTMENT_TIME", "STATUS",
            )]
            self._many = list(self.database.related_records["appointments"])
        elif "FROM ADMISSION A" in normalized and "WHERE A.PATIENT_ID = :PATIENT_ID" in normalized:
            self.description = [(name,) for name in (
                "ADMISSION_ID", "PATIENT_ID", "PATIENT_NAME", "ROOM_ID", "ROOM_NUMBER",
                "ADMISSION_DATE", "DISCHARGE_DATE",
            )]
            self._many = list(self.database.related_records["admissions"])
        elif "FROM PRESCRIPTION RX" in normalized and "WHERE RX.PATIENT_ID = :PATIENT_ID" in normalized:
            self.description = [(name,) for name in (
                "PRESCRIPTION_ID", "PATIENT_ID", "PATIENT_NAME", "DOCTOR_ID", "DOCTOR_NAME",
                "MEDICINE_ID", "MEDICINE_NAME", "DOSAGE", "DURATION", "PRESCRIPTION_DATE",
            )]
            self._many = list(self.database.related_records["prescriptions"])
        elif "FROM BILL B" in normalized and "WHERE B.PATIENT_ID = :PATIENT_ID" in normalized:
            self.description = [(name,) for name in (
                "BILL_ID", "PATIENT_ID", "PATIENT_NAME", "BILL_DATE", "CONSULTATION_CHARGE",
                "ROOM_CHARGE", "MEDICINE_CHARGE", "TOTAL_AMOUNT", "PAYMENT_STATUS",
            )]
            self._many = list(self.database.related_records["bills"])
        elif normalized.startswith("SELECT DEP.DEPARTMENT_ID AS DEPARTMENT_ID"):
            self.description = [(name,) for name in ("DEPARTMENT_ID", "DEPARTMENT_NAME", "LOCATION", "DOCTOR_COUNT")]
            self._many = list(self.database.report_rows)
        elif normalized.startswith("SELECT (SELECT COUNT(*) FROM PATIENT)"):
            summary_columns = (
                "PATIENTS", "DOCTORS", "DEPARTMENTS", "APPOINTMENTS",
                "UPCOMING_APPOINTMENTS", "TODAY_QUEUE_APPOINTMENTS", "COMPLETED_APPOINTMENTS", "CANCELLED_APPOINTMENTS",
                "ACTIVE_ADMISSIONS", "TOTAL_ROOMS", "AVAILABLE_ROOMS", "OCCUPIED_ROOMS",
                "MAINTENANCE_ROOMS", "TOTAL_MEDICINES", "LOW_STOCK_MEDICINES",
                "PENDING_BILLS", "PAID_BILLS", "OUTSTANDING_TOTAL", "COLLECTED_TOTAL",
            )
            self.description = [(column,) for column in summary_columns]
            self._one = tuple(Decimal("0") if column.endswith("_TOTAL") else 0 for column in summary_columns)
        elif normalized.startswith("SELECT COUNT(*)"):
            self.description = [("COUNT(*)",)]
            self._one = (0,)
        elif normalized.startswith("SELECT STOCK_QUANTITY FROM MEDICINE"):
            self.description = [("STOCK_QUANTITY",)]
            self._one = (self.database.stock_quantity,)
        elif normalized.startswith("SELECT DISCHARGE_DATE FROM ADMISSION"):
            self.description = [("DISCHARGE_DATE",)]
            self._one = self.database.admission_row
        elif normalized.startswith("SELECT"):
            self.description = [("DEPARTMENT_ID",), ("DEPARTMENT_NAME",), ("LOCATION",), ("DOCTOR_COUNT",)]
            self._one = None
            self._many = []
        elif normalized.startswith("UPDATE"):
            self.rowcount = self.database.update_rowcount
            self.description = [("STOCK_QUANTITY",)]
            self._one = (self.database.stock_quantity,)
        elif normalized.startswith("DELETE"):
            self.rowcount = 1
        return self

    def fetchone(self):
        value = self._one
        self._one = None
        return value

    def fetchall(self):
        values = self._many
        self._many = []
        return values


class FakeConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self):
        return FakeCursor(self.database)

    def commit(self):
        self.database.commits += 1

    def rollback(self):
        self.database.rollbacks += 1


class FakeDatabase:
    def __init__(self, execute_error=None, returning_id=41, update_rowcount=1, stock_quantity=7,
                 admission_row=None, appointment_row=None, database_today=None,
                 queue_rows=None, report_rows=None, patient_record=None, related_records=None):
        self.execute_error = execute_error
        self.returning_id = returning_id
        self.update_rowcount = update_rowcount
        self.stock_quantity = stock_quantity
        self.admission_row = admission_row
        self.appointment_row = appointment_row
        self.database_today = database_today or datetime.combine(date.today(), time.min)
        self.queue_rows = queue_rows or []
        self.report_rows = report_rows or []
        self.patient_record = patient_record
        self.related_records = related_records or {
            "appointments": [], "admissions": [], "prescriptions": [], "bills": [],
        }
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.connection_count = 0

    @contextmanager
    def connection(self):
        self.connection_count += 1
        yield FakeConnection(self)


class ValidationTests(unittest.TestCase):
    def test_required_and_enum_values_are_validated(self):
        with self.assertRaises(ApiError):
            _validate_payload(RESOURCES["patients"], {
                "patient_name": "Sample", "date_of_birth": "2000-01-01", "gender": "X",
            }, partial=False)

    def test_negative_bill_charge_is_rejected(self):
        with self.assertRaises(ApiError):
            _validate_payload(RESOURCES["bills"], {
                "patient_id": 1, "bill_date": "2026-01-01",
                "consultation_charge": "-0.01", "room_charge": "0", "medicine_charge": "0",
                "payment_status": "Pending",
            }, partial=False)

    def test_money_keeps_two_decimal_precision(self):
        values = _validate_payload(RESOURCES["bills"], {
            "patient_id": "4", "bill_date": "2026-01-01",
            "consultation_charge": "125.50", "room_charge": "0", "medicine_charge": "2.25",
            "payment_status": "Paid",
        }, partial=False)
        self.assertEqual(values["consultation_charge"], Decimal("125.50"))
        self.assertEqual(values["patient_id"], 4)

    def test_appointment_time_and_iso_date_are_strict(self):
        base = {"patient_id": 1, "doctor_id": 2, "appointment_date": "2026-11-15", "status": "Scheduled"}
        with self.assertRaises(ApiError):
            _validate_payload(RESOURCES["appointments"], {**base, "appointment_time": "25:99"}, partial=False)
        with self.assertRaises(ApiError):
            _validate_payload(RESOURCES["appointments"], {**base, "appointment_date": "20261115", "appointment_time": "10:00"}, partial=False)

    def test_negative_stock_and_invalid_room_state_are_rejected(self):
        with self.assertRaises(ApiError):
            _validate_payload(RESOURCES["medicines"], {
                "medicine_name": "Example", "price": "3.25", "stock_quantity": -1,
            }, partial=False)
        with self.assertRaises(ApiError):
            _validate_payload(RESOURCES["rooms"], {
                "room_number": "R-1", "room_type": "General", "availability_status": "In use",
            }, partial=False)

    def test_completed_appointments_can_retain_historical_dates(self):
        values = _validate_payload(RESOURCES["appointments"], {
            "patient_id": 1, "doctor_id": 2, "appointment_date": "2001-01-01",
            "appointment_time": "09:30", "status": "Completed",
        }, partial=False)
        self.assertEqual(values["appointment_date"], datetime(2001, 1, 1))

    def test_date_of_birth_cannot_be_in_future(self):
        future = date.today().replace(year=date.today().year + 1).isoformat()
        with self.assertRaises(ApiError):
            _validate_payload(RESOURCES["patients"], {
                "patient_name": "Future", "date_of_birth": future, "gender": "O",
            }, partial=False)


class AppointmentAndExportHelperTests(unittest.TestCase):
    def test_status_vocabulary_covers_queue_and_terminal_states(self):
        self.assertEqual(APPOINTMENT_STATUSES, (
            "Scheduled", "Checked In", "Waiting", "In Consultation",
            "Completed", "Cancelled", "No-show",
        ))

    def test_patient_timeline_merges_only_stored_events_in_date_order(self):
        timeline = _patient_timeline({
            "appointments": [{
                "appointment_id": 2, "appointment_date": "2026-06-10", "appointment_time": "09:00",
                "doctor_name": "Dr. Rao", "department_name": "Cardiology", "status": "Completed",
            }],
            "admissions": [{
                "admission_id": 3, "admission_date": "2026-06-11", "discharge_date": "2026-06-12",
                "room_number": "R-1",
            }],
            "prescriptions": [{
                "prescription_id": 4, "prescription_date": "2026-06-13", "medicine_name": "Example",
                "dosage": "1 tablet", "duration": "5 days", "doctor_name": "Dr. Rao",
            }],
            "bills": [{
                "bill_id": 5, "bill_date": "2026-06-14", "total_amount": 10.0,
                "payment_status": "Pending",
            }],
        })
        self.assertEqual([event["date"] for event in timeline], [
            "2026-06-14", "2026-06-13", "2026-06-12", "2026-06-11", "2026-06-10",
        ])
        self.assertIn("₹10.00", timeline[0]["details"])
        self.assertEqual(timeline[1]["type"], "Prescription")
        self.assertIn("dispensing not recorded", timeline[1]["status"])
        self.assertEqual(timeline[2]["type"], "Discharge")

    def test_csv_values_preserve_numbers_and_neutralize_formula_text(self):
        self.assertEqual(_csv_value(Decimal("12.30")), "12.30")
        self.assertEqual(_csv_value("=1+1"), "'=1+1")
        self.assertEqual(_csv_value("  +SUM(A1:A2)"), "'  +SUM(A1:A2)")
        self.assertEqual(_csv_value("\t=cmd"), "'\t=cmd")


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        self.app = create_app(database=self.database, test_config={"TESTING": True})
        self.client = self.app.test_client()

    def test_static_application_is_served_with_security_headers(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CarePoint", response.data)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        response.close()
        script = self.client.get("/static/app.js")
        self.assertEqual(script.status_code, 200)
        self.assertIn(b"/api/dashboard", script.data)
        script.close()

    def test_health_uses_database_and_returns_json(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["database"], "oracle")
        self.assertEqual(self.database.calls[0][0], "SELECT 1 AS ok FROM dual")

    def test_missing_oracle_configuration_returns_safe_503(self):
        app = create_app(database=OracleDatabase(), test_config={"TESTING": True})
        response = app.test_client().get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("password", response.get_data(as_text=True).lower())

    def test_invalid_input_fails_before_database_access(self):
        response = self.client.post("/api/departments", json={"department_name": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("required", response.get_json()["error"]["message"].lower())
        self.assertEqual(self.database.connection_count, 0)

    def test_valid_create_is_parameterized_and_committed(self):
        response = self.client.post("/api/departments", json={
            "department_name": "Cardiology' OR '1'='1", "location": "Block A",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["data"]["id"], 41)
        sql, binds = self.database.calls[0]
        self.assertIn(":department_name", sql)
        self.assertNotIn("Cardiology' OR", sql)
        self.assertEqual(binds["department_name"], "Cardiology' OR '1'='1")
        self.assertEqual(self.database.commits, 1)
        self.assertEqual(self.database.rollbacks, 0)

    def test_oracle_unique_error_rolls_back_and_maps_to_conflict(self):
        database = FakeDatabase(execute_error=FakeOracleError("ORA-00001: unique constraint"))
        app = create_app(database=database, test_config={"TESTING": True})
        response = app.test_client().post("/api/departments", json={
            "department_name": "Duplicate", "location": "Block A",
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["error"]["code"], "conflict")
        self.assertEqual(database.rollbacks, 1)
        self.assertEqual(database.commits, 0)
        self.assertNotIn("ORA-00001", response.get_data(as_text=True))

    def test_database_unavailable_does_not_expose_driver_details(self):
        database = FakeDatabase(execute_error=FakeOracleError("ORA-12541: connect refused with secret details"))
        app = create_app(database=database, test_config={"TESTING": True})
        response = app.test_client().get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret details", response.get_data(as_text=True))

    def test_unknown_resource_is_structured_404(self):
        response = self.client.get("/api/not-a-table")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "not_found")

    def test_room_cannot_be_created_as_occupied(self):
        response = self.client.post("/api/rooms", json={
            "room_number": "R-1", "room_type": "Private", "availability_status": "Occupied",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.database.connection_count, 0)


    def test_filtered_search_uses_bound_parameters(self):
        term = "x%' OR 1=1 --"
        response = self.client.get("/api/doctors", query_string={"q": term})
        self.assertEqual(response.status_code, 200)
        sql, binds = self.database.calls[0]
        self.assertIn(":q", sql)
        self.assertNotIn(term, sql)
        self.assertEqual(binds["q"], f"%{term.upper()}%")

    def test_dashboard_returns_database_derived_sections(self):
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(data["counts"]["patients"], 0)
        self.assertIn("today_queue_appointments", data["counts"])
        self.assertIn("upcoming_appointments", data)
        self.assertIn("outstanding_bills", data)
        self.assertIn("low_stock_medicines", data)
        self.assertIn("recent_records", data)
        self.assertEqual(len(self.database.calls), 5)
        self.assertIn("FROM dual", self.database.calls[0][0])

    def test_resource_list_paginates_filters_and_clamps_out_of_range_page(self):
        response = self.client.get("/api/appointments", query_string={
            "page": 5, "page_size": 10, "status": "Scheduled",
            "date_from": "2026-11-01", "date_to": "2026-11-02",
        })
        self.assertEqual(response.status_code, 200)
        pagination = response.get_json()["meta"]["pagination"]
        self.assertEqual(pagination, {"page": 1, "page_size": 10, "total": 0, "pages": 1})
        count_sql, count_binds = self.database.calls[0]
        data_sql, data_binds = self.database.calls[1]
        self.assertIn("a.status = :filter_status", count_sql)
        self.assertIn("a.appointment_date >= :date_from", count_sql)
        self.assertIn("a.appointment_date < :date_to", count_sql)
        self.assertEqual(count_binds["filter_status"], "Scheduled")
        self.assertEqual(data_binds["page_offset"], 0)
        self.assertIn("OFFSET :page_offset ROWS FETCH NEXT :page_size ROWS ONLY", data_sql)

    def test_report_list_paginates_and_rejects_unknown_report(self):
        response = self.client.get("/api/reports/patient-appointments", query_string={
            "patient_id": "31", "page": "8", "page_size": "10",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["meta"]["pagination"]["page"], 1)
        count_sql, count_binds = self.database.calls[0]
        self.assertIn("a.patient_id = :filter_patient_id", count_sql)
        self.assertEqual(count_binds["filter_patient_id"], 31)
        unknown = self.client.get("/api/reports/not-a-report")
        self.assertEqual(unknown.status_code, 404)

    def test_report_csv_exports_all_filtered_rows_without_page_limits(self):
        database = FakeDatabase(report_rows=[
            (1, datetime(2026, 6, 1), "09:00", "Waiting", 31, "=1+1", 7, "Dr. Rao", "Cardiology"),
            (2, datetime(2026, 6, 2), "10:00", "Completed", 31, "Asha Patient", 7, "Dr. Rao", "Cardiology"),
        ])
        app = create_app(database=database, test_config={"TESTING": True})
        response = app.test_client().get("/api/reports/patient-appointments/csv", query_string={
            "patient_id": "31", "status": "Waiting", "date_from": "2026-06-01",
            "date_to": "2026-06-30", "page": "99", "page_size": "1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/csv")
        self.assertIn("filename=\"patient-appointments.csv\"", response.headers["Content-Disposition"])
        sql, binds = database.calls[0]
        self.assertIn("a.patient_id = :filter_patient_id", sql)
        self.assertIn("a.status = :filter_status", sql)
        self.assertIn("a.appointment_date >= :date_from", sql)
        self.assertIn("a.appointment_date < :date_to", sql)
        self.assertNotIn("OFFSET", sql.upper())
        self.assertEqual(binds["filter_patient_id"], 31)
        self.assertEqual(binds["filter_status"], "Waiting")
        self.assertEqual(len(response.get_data(as_text=True).splitlines()), 3)
        self.assertIn("'=1+1", response.get_data(as_text=True))

    def test_appointment_queue_is_date_and_doctor_filtered_and_ordered(self):
        today = datetime.combine(date.today(), time.min)
        database = FakeDatabase(queue_rows=[
            (2, 22, "Waiting Patient", 7, "Dr. Rao", "Cardiology", today, "09:00", "Waiting"),
            (1, 21, "Scheduled Patient", 7, "Dr. Rao", "Cardiology", today, "10:00", "Scheduled"),
        ])
        app = create_app(database=database, test_config={"TESTING": True})
        response = app.test_client().get("/api/appointments/queue?date=" + date.today().isoformat() + "&doctor_id=7")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(data["counts"]["Waiting"], 1)
        self.assertEqual(data["counts"]["Scheduled"], 1)
        self.assertEqual(data["next_patient"]["patient_name"], "Waiting Patient")
        sql, binds = database.calls[0]
        self.assertIn("a.appointment_date = :queue_date", sql)
        self.assertIn("a.doctor_id = :doctor_id", sql)
        self.assertIn("ORDER BY CASE a.status", sql)
        self.assertIn("WHEN 'Waiting' THEN 1", sql)
        self.assertEqual(binds["doctor_id"], 7)
        invalid = app.test_client().get("/api/appointments/queue?date=not-a-date")
        self.assertEqual(invalid.status_code, 400)

    def test_patient_summary_includes_database_derived_unified_timeline(self):
        database = FakeDatabase(
            patient_record=(31, "Asha Patient", datetime(1990, 1, 2), "F", "+91-90000-00000", "Vellore", "O+"),
            related_records={
                "appointments": [(2, 31, "Asha Patient", 7, "Dr. Rao", "Cardiology", datetime(2026, 6, 1), "09:00", "Completed")],
                "admissions": [(3, 31, "Asha Patient", 2, "R-1", datetime(2026, 6, 2), datetime(2026, 6, 3))],
                "prescriptions": [(4, 31, "Asha Patient", 7, "Dr. Rao", 5, "Example medicine", "1 tablet", "5 days", datetime(2026, 6, 4))],
                "bills": [(5, 31, "Asha Patient", datetime(2026, 6, 5), Decimal("10.00"), Decimal("0"), Decimal("0"), Decimal("10.00"), "Pending")],
            },
        )
        app = create_app(database=database, test_config={"TESTING": True})
        response = app.test_client().get("/api/patients/31/summary")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(data["patient"]["patient_id"], 31)
        self.assertEqual([event["type"] for event in data["timeline"]], [
            "Bill", "Prescription", "Discharge", "Admission", "Appointment",
        ])
        self.assertIn("dispensing not recorded", data["timeline"][1]["status"])
        self.assertEqual(len(database.calls), 5)

    def test_low_stock_and_report_page_size_filters_are_validated(self):
        response = self.client.get("/api/medicines?low_stock=true")
        self.assertEqual(response.status_code, 200)
        self.assertIn("m.stock_quantity < 10", self.database.calls[0][0])
        self.database.calls.clear()
        invalid = self.client.get("/api/reports/patient-appointments?page_size=101")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.database.calls, [])

    def test_appointment_and_admission_histories_cannot_be_deleted(self):
        for resource, record_id in (("appointments", 19), ("prescriptions", 20), ("bills", 21)):
            response = self.client.delete(f"/api/{resource}/{record_id}")
            self.assertEqual(response.status_code, 409)
        direct_discharge = self.client.put("/api/admissions/20", json={"discharge_date": "2026-10-27"})
        self.assertEqual(direct_discharge.status_code, 400)
        self.assertEqual(self.database.connection_count, 0)

        for row, error_code in (((None,), "active_admission"), ((datetime(2024, 1, 1),), "admission_history")):
            database = FakeDatabase(admission_row=row)
            app = create_app(database=database, test_config={"TESTING": True})
            response = app.test_client().delete("/api/admissions/20")
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.get_json()["error"]["code"], error_code)
            self.assertEqual(database.commits, 0)

    def test_stock_change_is_atomic_and_parameterized(self):
        response = self.client.post("/api/medicines/8/stock-adjustments", json={"change": -2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["stock_quantity"], 7)
        update_sql, binds = self.database.calls[0]
        self.assertIn("STOCK_QUANTITY + :CHANGE BETWEEN 0 AND 9999999999", update_sql.upper())
        self.assertEqual(binds["change"], -2)
        self.assertEqual(self.database.commits, 1)

    def test_stock_cannot_be_set_through_regular_medicine_update(self):
        response = self.client.put("/api/medicines/8", json={"stock_quantity": 100})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.database.connection_count, 0)

    def test_scheduled_appointment_in_the_past_is_rejected_before_sql(self):
        response = self.client.post("/api/appointments", json={
            "patient_id": 1, "doctor_id": 1, "appointment_date": "2001-01-01",
            "appointment_time": "09:00", "status": "Scheduled",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.database.connection_count, 0)

    def test_appointment_creation_must_start_scheduled(self):
        response = self.client.post("/api/appointments", json={
            "patient_id": 1, "doctor_id": 2, "appointment_date": date.today().isoformat(),
            "appointment_time": "09:00", "status": "Completed",
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("start as scheduled", response.get_json()["error"]["message"].lower())
        self.assertEqual(self.database.connection_count, 0)

    def test_appointment_workflow_rejects_skipped_states_and_checks_in_on_the_db_date(self):
        today = datetime.combine(date.today(), time.min)
        invalid_database = FakeDatabase(appointment_row=(1, 2, today, "09:00", "Scheduled"))
        invalid_app = create_app(database=invalid_database, test_config={"TESTING": True})
        invalid = invalid_app.test_client().put("/api/appointments/12", json={"status": "Completed"})
        self.assertEqual(invalid.status_code, 409)
        self.assertEqual(invalid.get_json()["error"]["code"], "invalid_status_transition")
        self.assertFalse(any(sql.lstrip().upper().startswith("UPDATE APPOINTMENT") for sql, _ in invalid_database.calls))

        database = FakeDatabase(appointment_row=(1, 2, today, "09:00", "Scheduled"))
        app = create_app(database=database, test_config={"TESTING": True})
        response = app.test_client().put("/api/appointments/12", json={"status": "Checked In"})
        self.assertEqual(response.status_code, 200)
        update_sql = next(sql for sql, _ in database.calls if sql.lstrip().upper().startswith("UPDATE APPOINTMENT"))
        self.assertIn("status = :status", update_sql)
        self.assertEqual(database.commits, 1)

    def test_check_in_and_no_show_date_rules_are_enforced_before_update(self):
        today = datetime.combine(date.today(), time.min)
        future = datetime.combine(date.today() + timedelta(days=1), time.min)
        database = FakeDatabase(appointment_row=(1, 2, future, "09:00", "Scheduled"))
        app = create_app(database=database, test_config={"TESTING": True})
        check_in = app.test_client().put("/api/appointments/12", json={"status": "Checked In"})
        self.assertEqual(check_in.status_code, 409)
        self.assertEqual(check_in.get_json()["error"]["code"], "appointment_not_today")
        self.assertFalse(any(sql.lstrip().upper().startswith("UPDATE APPOINTMENT") for sql, _ in database.calls))

        database = FakeDatabase(appointment_row=(1, 2, today, "09:00", "Scheduled"))
        app = create_app(database=database, test_config={"TESTING": True})
        no_show = app.test_client().put("/api/appointments/12", json={"status": "No-show"})
        self.assertEqual(no_show.status_code, 409)
        self.assertEqual(no_show.get_json()["error"]["code"], "appointment_not_overdue")
        self.assertFalse(any(sql.lstrip().upper().startswith("UPDATE APPOINTMENT") for sql, _ in database.calls))

    def test_sql_integrity_and_seed_guards_are_declared(self):
        from pathlib import Path
        schema = Path("sql/01_create_schema.sql").read_text(encoding="utf-8")
        self.assertIn("uq_appointment_doctor_slot", schema.lower())
        self.assertIn("uq_appointment_patient_slot", schema.lower())
        self.assertIn("uq_admission_active_room", schema.lower())
        self.assertIn("number(11,2) generated always as", schema.lower())
        seeds = Path("sql/02_sample_data.sql").read_text(encoding="utf-8").lower()
        self.assertGreaterEqual(seeds.count("a.patient_id = p.patient_id"), 2)
        self.assertIn("a.status in ('scheduled', 'checked in', 'waiting', 'in consultation')", seeds)
        self.assertIn("set status = 'checked in'", seeds)
        self.assertIn("set status = 'completed'", seeds)
        self.assertIn("returning appointment_id into v_appointment_id", seeds)
        self.assertEqual(seeds.count("where appointment_id = v_appointment_id"), 5)
        self.assertIn("'no-show'", schema.lower())
        self.assertIn(":old.status = 'waiting' and :new.status = 'in consultation'", schema.lower())


if __name__ == "__main__":
    unittest.main()
