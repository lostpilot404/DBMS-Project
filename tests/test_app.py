"""API and validation regression tests; no Oracle service is required."""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

from hms import create_app
from hms.api import ApiError, RESOURCES, _validate_payload
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
        elif normalized.startswith("SELECT (SELECT COUNT(*) FROM PATIENT)"):
            summary_columns = (
                "PATIENTS", "DOCTORS", "DEPARTMENTS", "APPOINTMENTS",
                "UPCOMING_APPOINTMENTS", "COMPLETED_APPOINTMENTS", "CANCELLED_APPOINTMENTS",
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
    def __init__(self, execute_error=None, returning_id=41, update_rowcount=1, stock_quantity=7, admission_row=None):
        self.execute_error = execute_error
        self.returning_id = returning_id
        self.update_rowcount = update_rowcount
        self.stock_quantity = stock_quantity
        self.admission_row = admission_row
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

    def test_sql_integrity_and_seed_guards_are_declared(self):
        from pathlib import Path
        schema = Path("sql/01_create_schema.sql").read_text(encoding="utf-8")
        self.assertIn("uq_appointment_doctor_slot", schema.lower())
        self.assertIn("uq_appointment_patient_slot", schema.lower())
        self.assertIn("uq_admission_active_room", schema.lower())
        self.assertIn("number(11,2) generated always as", schema.lower())
        seeds = Path("sql/02_sample_data.sql").read_text(encoding="utf-8").lower()
        self.assertGreaterEqual(seeds.count("a.patient_id = p.patient_id"), 2)
        self.assertIn("a.status = 'scheduled'", seeds)


if __name__ == "__main__":
    unittest.main()
