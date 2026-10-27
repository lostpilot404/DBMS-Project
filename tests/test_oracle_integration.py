"""Opt-in integration tests against a real, configured Oracle 12c+ schema.

These tests never mock the driver and never drop tables. They create uniquely
named synthetic rows through the Flask API, exercise Oracle constraints and
triggers, then remove only rows belonging to their own generated IDs.
"""
from __future__ import annotations

import os
import threading
import time
import unittest
import uuid
from datetime import date, timedelta

import oracledb
from dotenv import load_dotenv

from hms import create_app
from hms.database import OracleDatabase


REQUIRED_TABLES = {
    "DEPARTMENT", "DOCTOR", "PATIENT", "APPOINTMENT", "ROOM",
    "ADMISSION", "MEDICINE", "PRESCRIPTION", "BILL",
}
TRIGGERS = {
    "TRG_APPOINTMENT_GUARD",
    "TRG_ADMISSION_ROOM_GUARD",
    "TRG_ADMISSION_ROOM_SYNC",
    "TRG_ADMISSION_DELETE_GUARD",
}
TEST_SCHEMA = "HMS_ORACLE_TEST"
TEST_ACK = "I_CONFIRM_HMS_ORACLE_TEST_IS_DISPOSABLE"


def _validate_test_schema_identity(configured_user, session_user=None, current_schema=None):
    """Reject generic/test-like accounts and schema switching before any test writes."""
    if str(configured_user or "").strip().upper() != TEST_SCHEMA:
        raise RuntimeError(f"ORACLE_USER must be exactly {TEST_SCHEMA} for live integration tests.")
    if session_user is not None and str(session_user).strip().upper() != TEST_SCHEMA:
        raise RuntimeError(f"Oracle SESSION_USER must be exactly {TEST_SCHEMA} for live integration tests.")
    if current_schema is not None and str(current_schema).strip().upper() != TEST_SCHEMA:
        raise RuntimeError(f"Oracle CURRENT_SCHEMA must be exactly {TEST_SCHEMA} for live integration tests.")


class OracleSafetyGuardTests(unittest.TestCase):
    def test_exact_dedicated_schema_identity_is_accepted(self):
        _validate_test_schema_identity("hms_oracle_test", "HMS_ORACLE_TEST", "hms_oracle_test")

    def test_generic_or_test_like_users_are_rejected(self):
        for username in ("HMS_APP", "HMS_TEST", "HMS_ORACLE_TESTING", "", None):
            with self.subTest(username=username), self.assertRaises(RuntimeError):
                _validate_test_schema_identity(username)

    def test_session_user_and_current_schema_must_both_match_exactly(self):
        for session_user, current_schema in (
            ("HMS_APP", TEST_SCHEMA),
            (TEST_SCHEMA, "HMS_APP"),
            ("MY_TEST_USER", "MY_TEST_USER"),
        ):
            with self.subTest(session_user=session_user, current_schema=current_schema), self.assertRaises(RuntimeError):
                _validate_test_schema_identity(TEST_SCHEMA, session_user, current_schema)


@unittest.skipUnless(
    os.environ.get("HMS_ORACLE_INTEGRATION") == "1"
    and os.environ.get("HMS_ORACLE_TEST_ACK") == TEST_ACK,
    "Live Oracle tests require HMS_ORACLE_INTEGRATION=1 and an explicit disposable-schema acknowledgement.",
)
class OracleIntegrationTests(unittest.TestCase):
    """Run only on the dedicated disposable schema documented in README.md."""

    @classmethod
    def setUpClass(cls):
        # app.py normally loads .env. Do the same here so local credentials work
        # when this module is invoked directly by unittest.
        load_dotenv()
        if os.getenv("HMS_ORACLE_TEST_ACK") != TEST_ACK:
            raise RuntimeError("Refusing live tests without the disposable-schema acknowledgement.")
        _validate_test_schema_identity(os.getenv("ORACLE_USER"))
        cls.database = OracleDatabase.from_environment()
        if not cls.database.configured:
            raise RuntimeError(
                "Oracle integration was enabled, but ORACLE_USER, "
                "ORACLE_PASSWORD, and ORACLE_DSN are not all configured."
            )
        # Verify both the authenticated account and active schema before any test
        # mutation. A generic username containing TEST is not sufficient.
        with cls.database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT SYS_CONTEXT('USERENV', 'SESSION_USER'), "
                    "SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM dual"
                )
                session_user, current_schema = cursor.fetchone()
        try:
            _validate_test_schema_identity(os.getenv("ORACLE_USER"), session_user, current_schema)
        except RuntimeError:
            cls.database.close()
            raise
        cls.app = create_app(database=cls.database, test_config={"TESTING": True})
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.database.close()

    def setUp(self):
        self.token = uuid.uuid4().hex[:12].upper()
        self.ids: dict[str, list[int]] = {
            "departments": [], "doctors": [], "patients": [],
            "rooms": [], "medicines": [],
        }
        try:
            self.department_id = self._create("departments", {
                "department_name": f"Oracle IT {self.token}",
                "location": "Disposable integration schema",
            })
            self.doctor_id = self._create_doctor("A")
            self.patient_id = self._create_patient("A")
            self.room_id = self._create_room("A")
            self.medicine_id = self._create("medicines", {
                "medicine_name": f"Oracle IT medicine {self.token}",
                "manufacturer": "Integration test only",
                "price": 1.25,
                "stock_quantity": 5,
            })
        except BaseException:
            self._cleanup()
            raise

    def tearDown(self):
        self._cleanup()

    def _create(self, resource: str, payload: dict) -> int:
        response = self.client.post(f"/api/{resource}", json=payload)
        self.assertEqual(response.status_code, 201, response.get_json())
        record_id = int(response.get_json()["data"]["id"])
        self.ids[resource].append(record_id)
        return record_id

    def _create_doctor(self, suffix: str) -> int:
        return self._create("doctors", {
            "doctor_name": f"Oracle IT doctor {self.token} {suffix}",
            "specialization": "Integration testing",
            "department_id": self.department_id,
            "email": f"oracle-it-{self.token}-{suffix.lower()}@example.test",
        })

    def _create_patient(self, suffix: str) -> int:
        phone_tail = str(uuid.uuid4().int % 10_000_000_000).zfill(10)
        return self._create("patients", {
            "patient_name": f"Oracle IT patient {self.token} {suffix}",
            "date_of_birth": "1990-01-01",
            "gender": "O",
            "phone": f"+91-9{phone_tail}",
        })

    def _create_room(self, suffix: str) -> int:
        return self._create("rooms", {
            "room_number": f"IT-{self.token[:8]}-{suffix}",
            "room_type": "General",
            "availability_status": "Available",
        })

    def _cleanup(self):
        """Delete only synthetic rows linked to tracked IDs; never drop objects."""
        if not getattr(self, "ids", None):
            return
        with self.database.connection() as connection:
            try:
                with connection.cursor() as cursor:
                    for patient_id in self.ids["patients"]:
                        # The admission trigger restores room state before the row is removed.
                        cursor.execute(
                            "UPDATE Admission SET discharge_date = SYSDATE "
                            "WHERE patient_id = :patient_id AND discharge_date IS NULL",
                            {"patient_id": patient_id},
                        )
                        cursor.execute("DELETE FROM Appointment WHERE patient_id = :id", {"id": patient_id})
                        cursor.execute("DELETE FROM Prescription WHERE patient_id = :id", {"id": patient_id})
                        cursor.execute("DELETE FROM Bill WHERE patient_id = :id", {"id": patient_id})
                        cursor.execute("DELETE FROM Admission WHERE patient_id = :id", {"id": patient_id})
                    for doctor_id in self.ids["doctors"]:
                        cursor.execute("DELETE FROM Appointment WHERE doctor_id = :id", {"id": doctor_id})
                        cursor.execute("DELETE FROM Prescription WHERE doctor_id = :id", {"id": doctor_id})
                    for medicine_id in self.ids["medicines"]:
                        cursor.execute("DELETE FROM Prescription WHERE medicine_id = :id", {"id": medicine_id})
                    for room_id in self.ids["rooms"]:
                        cursor.execute("DELETE FROM Admission WHERE room_id = :id", {"id": room_id})
                    for doctor_id in self.ids["doctors"]:
                        cursor.execute("DELETE FROM Doctor WHERE doctor_id = :id", {"id": doctor_id})
                    for patient_id in self.ids["patients"]:
                        cursor.execute("DELETE FROM Patient WHERE patient_id = :id", {"id": patient_id})
                    for room_id in self.ids["rooms"]:
                        cursor.execute("DELETE FROM Room WHERE room_id = :id", {"id": room_id})
                    for medicine_id in self.ids["medicines"]:
                        cursor.execute("DELETE FROM Medicine WHERE medicine_id = :id", {"id": medicine_id})
                    for department_id in self.ids["departments"]:
                        cursor.execute("DELETE FROM Department WHERE department_id = :id", {"id": department_id})
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def _assert_oracle_error(self, code: int, sql: str, binds: dict):
        with self.database.connection() as connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql, binds)
            except oracledb.Error as error:
                connection.rollback()
                self.assertIn(f"ORA-{code:05d}", str(error))
            else:
                connection.rollback()
                self.fail(f"Expected Oracle to reject the statement with ORA-{code:05d}.")

    def _room_status(self, room_id: int) -> str:
        response = self.client.get(f"/api/rooms/{room_id}")
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()["data"]["availability_status"]

    def test_schema_metadata_and_workflow_triggers_are_valid(self):
        with self.database.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT table_name FROM user_tables "
                    "WHERE table_name IN ("
                    "'DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',"
                    "'ADMISSION','MEDICINE','PRESCRIPTION','BILL')"
                )
                tables = {row[0] for row in cursor.fetchall()}
                self.assertEqual(tables, REQUIRED_TABLES)

                cursor.execute(
                    "SELECT object_name, status FROM user_objects "
                    "WHERE object_type = 'TRIGGER' AND object_name IN ("
                    "'TRG_APPOINTMENT_GUARD','TRG_ADMISSION_ROOM_GUARD',"
                    "'TRG_ADMISSION_ROOM_SYNC','TRG_ADMISSION_DELETE_GUARD')"
                )
                trigger_rows = cursor.fetchall()
                self.assertEqual({row[0] for row in trigger_rows}, TRIGGERS)
                self.assertTrue(all(row[1] == "VALID" for row in trigger_rows), trigger_rows)

                cursor.execute(
                    "SELECT COUNT(*) FROM user_tab_cols "
                    "WHERE table_name IN ("
                    "'DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',"
                    "'ADMISSION','MEDICINE','PRESCRIPTION','BILL') "
                    "AND identity_column = 'YES'"
                )
                self.assertEqual(cursor.fetchone()[0], 9)

                cursor.execute(
                    "SELECT COUNT(*) FROM user_constraints "
                    "WHERE constraint_type = 'R' AND status = 'ENABLED'"
                )
                self.assertEqual(cursor.fetchone()[0], 9)

    def test_database_checks_and_virtual_bill_total(self):
        self._assert_oracle_error(
            2290,
            "INSERT INTO Patient (patient_name, date_of_birth, gender) "
            "VALUES (:name, DATE '1990-01-01', 'X')",
            {"name": f"Invalid gender {self.token}"},
        )
        self._assert_oracle_error(
            2290,
            "INSERT INTO Patient (patient_name, date_of_birth, gender, blood_group) "
            "VALUES (:name, DATE '1990-01-01', 'M', 'ZZ')",
            {"name": f"Invalid blood group {self.token}"},
        )
        self._assert_oracle_error(
            2290,
            "INSERT INTO Bill (patient_id, consultation_charge, room_charge, medicine_charge) "
            "VALUES (:patient_id, -1, 0, 0)",
            {"patient_id": self.patient_id},
        )
        self._assert_oracle_error(
            2291,
            "INSERT INTO Doctor (doctor_name, specialization, department_id) "
            "VALUES (:name, 'Integration', -1)",
            {"name": f"Invalid department {self.token}"},
        )
        self._assert_oracle_error(
            2290,
            "INSERT INTO Appointment "
            "(patient_id, doctor_id, appointment_date, appointment_time, status) "
            "VALUES (:patient_id, :doctor_id, :appointment_date, '9:00', 'Scheduled')",
            {
                "patient_id": self.patient_id,
                "doctor_id": self.doctor_id,
                "appointment_date": date.today() + timedelta(days=2),
            },
        )
        self._assert_oracle_error(
            20022,
            "INSERT INTO Appointment "
            "(patient_id, doctor_id, appointment_date, appointment_time, status) "
            "VALUES (:patient_id, :doctor_id, :appointment_date, '09:00', 'Scheduled')",
            {
                "patient_id": self.patient_id,
                "doctor_id": self.doctor_id,
                "appointment_date": date.today() - timedelta(days=1),
            },
        )

        # The sum of three NUMBER(10,2) charge columns requires NUMBER(11,2).
        response = self.client.post("/api/bills", json={
            "patient_id": self.patient_id,
            "bill_date": date.today().isoformat(),
            "consultation_charge": 99_999_999.99,
            "room_charge": 99_999_999.99,
            "medicine_charge": 99_999_999.99,
            "payment_status": "Pending",
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        bill_id = response.get_json()["data"]["id"]
        bill = self.client.get(f"/api/bills/{bill_id}")
        self.assertEqual(bill.status_code, 200, bill.get_json())
        self.assertAlmostEqual(bill.get_json()["data"]["total_amount"], 299_999_999.97, places=2)
        retained_bill = self.client.delete(f"/api/bills/{bill_id}")
        self.assertEqual(retained_bill.status_code, 409, retained_bill.get_json())

        # A parent with dependent billing history is protected by the Oracle FK.
        deleted = self.client.delete(f"/api/patients/{self.patient_id}")
        self.assertEqual(deleted.status_code, 409, deleted.get_json())
        self.assertEqual(self.client.get(f"/api/patients/{self.patient_id}").status_code, 200)

    def test_appointment_conflicts_and_cancelled_slot_release(self):
        second_patient_id = self._create_patient("B")
        second_doctor_id = self._create_doctor("B")
        slot_date = (date.today() + timedelta(days=5)).isoformat()
        slot = {
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": slot_date,
            "appointment_time": "09:15",
            "status": "Scheduled",
        }
        first = self.client.post("/api/appointments", json=slot)
        self.assertEqual(first.status_code, 201, first.get_json())
        appointment_id = first.get_json()["data"]["id"]

        # Different patient, same doctor slot: protected by uq_appointment_doctor_slot.
        doctor_conflict = self.client.post("/api/appointments", json={**slot, "patient_id": second_patient_id})
        self.assertEqual(doctor_conflict.status_code, 409, doctor_conflict.get_json())

        # Same patient/time, different doctor: protected by uq_appointment_patient_slot.
        patient_conflict = self.client.post("/api/appointments", json={**slot, "doctor_id": second_doctor_id})
        self.assertEqual(patient_conflict.status_code, 409, patient_conflict.get_json())

        cancelled = self.client.put(f"/api/appointments/{appointment_id}", json={"status": "Cancelled"})
        self.assertEqual(cancelled.status_code, 200, cancelled.get_json())

        reopen = self.client.put(f"/api/appointments/{appointment_id}", json={"status": "Scheduled"})
        self.assertEqual(reopen.status_code, 409, reopen.get_json())
        self._assert_oracle_error(
            20020,
            "UPDATE Appointment SET status = 'Scheduled' WHERE appointment_id = :appointment_id",
            {"appointment_id": appointment_id},
        )
        delete_history = self.client.delete(f"/api/appointments/{appointment_id}")
        self.assertEqual(delete_history.status_code, 409, delete_history.get_json())

        released = self.client.post("/api/appointments", json={**slot, "patient_id": second_patient_id})
        self.assertEqual(released.status_code, 201, released.get_json())

    def test_admission_triggers_room_move_discharge_and_guards(self):
        second_patient_id = self._create_patient("B")
        second_room_id = self._create_room("B")
        test_admission_date = date(2020, 1, 1).isoformat()
        admission = self.client.post("/api/admissions", json={
            "patient_id": self.patient_id,
            "room_id": self.room_id,
            "admission_date": test_admission_date,
        })
        self.assertEqual(admission.status_code, 201, admission.get_json())
        admission_id = admission.get_json()["data"]["id"]
        self.assertEqual(self._room_status(self.room_id), "Occupied")

        # Active rows cannot be deleted, and a second patient cannot take this room.
        deletion = self.client.delete(f"/api/admissions/{admission_id}")
        self.assertEqual(deletion.status_code, 409, deletion.get_json())
        self._assert_oracle_error(
            20014,
            "DELETE FROM Admission WHERE admission_id = :id",
            {"id": admission_id},
        )
        occupied = self.client.post("/api/admissions", json={
            "patient_id": second_patient_id,
            "room_id": self.room_id,
            "admission_date": test_admission_date,
        })
        self.assertEqual(occupied.status_code, 409, occupied.get_json())

        # Exercise the database trigger's own date guard, not just API validation.
        self._assert_oracle_error(
            20010,
            "UPDATE Admission SET discharge_date = admission_date - 1 WHERE admission_id = :id",
            {"id": admission_id},
        )

        moved = self.client.put(f"/api/admissions/{admission_id}", json={"room_id": second_room_id})
        self.assertEqual(moved.status_code, 200, moved.get_json())
        self.assertEqual(self._room_status(self.room_id), "Available")
        self.assertEqual(self._room_status(second_room_id), "Occupied")

        # The patient still has one active stay, even though the original room is free.
        same_patient = self.client.post("/api/admissions", json={
            "patient_id": self.patient_id,
            "room_id": self.room_id,
            "admission_date": test_admission_date,
        })
        self.assertEqual(same_patient.status_code, 409, same_patient.get_json())

        discharge = self.client.post(
            f"/api/admissions/{admission_id}/discharge",
            json={"discharge_date": date.today().isoformat()},
        )
        self.assertEqual(discharge.status_code, 200, discharge.get_json())
        self.assertEqual(self._room_status(second_room_id), "Available")
        retained = self.client.delete(f"/api/admissions/{admission_id}")
        self.assertEqual(retained.status_code, 409, retained.get_json())
        self.assertEqual(retained.get_json()["error"]["code"], "admission_history")

        # A released room is reusable by another patient.
        rebook = self.client.post("/api/admissions", json={
            "patient_id": second_patient_id,
            "room_id": self.room_id,
            "admission_date": test_admission_date,
        })
        self.assertEqual(rebook.status_code, 201, rebook.get_json())

    def test_stock_adjustment_is_atomic_and_nonnegative(self):
        underflow = self.client.post(
            f"/api/medicines/{self.medicine_id}/stock-adjustments",
            json={"change": -6},
        )
        self.assertEqual(underflow.status_code, 409, underflow.get_json())

        added = self.client.post(
            f"/api/medicines/{self.medicine_id}/stock-adjustments",
            json={"change": 4},
        )
        self.assertEqual(added.status_code, 200, added.get_json())
        self.assertEqual(added.get_json()["data"]["stock_quantity"], 9)
        prescription = self.client.post("/api/prescriptions", json={
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "medicine_id": self.medicine_id,
            "dosage": "One tablet",
            "duration": "Five days",
            "prescription_date": date.today().isoformat(),
        })
        self.assertEqual(prescription.status_code, 201, prescription.get_json())
        retained = self.client.delete(f"/api/prescriptions/{prescription.get_json()['data']['id']}")
        self.assertEqual(retained.status_code, 409, retained.get_json())
        self._assert_oracle_error(
            2290,
            "UPDATE Medicine SET stock_quantity = -1 WHERE medicine_id = :id",
            {"id": self.medicine_id},
        )

    def test_concurrent_appointment_insert_is_serialized_by_oracle(self):
        """A racing duplicate must lose at Oracle's unique index, not an app precheck."""
        second_patient_id = self._create_patient("B")
        slot_date = date.today() + timedelta(days=8)
        parameters = {
            "doctor_id": self.doctor_id,
            "appointment_date": slot_date,
            "appointment_time": "16:45",
            "status": "Scheduled",
        }
        first = oracledb.connect(
            user=self.database.user, password=self.database.password, dsn=self.database.dsn,
        )
        second = oracledb.connect(
            user=self.database.user, password=self.database.password, dsn=self.database.dsn,
        )
        second.call_timeout = 20_000
        started = threading.Event()
        result: list[Exception | str] = []

        try:
            with first.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO Appointment "
                    "(patient_id, doctor_id, appointment_date, appointment_time, status) "
                    "VALUES (:patient_id, :doctor_id, :appointment_date, :appointment_time, :status)",
                    {**parameters, "patient_id": self.patient_id},
                )

            def insert_competing_slot():
                started.set()
                try:
                    with second.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO Appointment "
                            "(patient_id, doctor_id, appointment_date, appointment_time, status) "
                            "VALUES (:patient_id, :doctor_id, :appointment_date, :appointment_time, :status)",
                            {**parameters, "patient_id": second_patient_id},
                        )
                    second.commit()
                    result.append("inserted")
                except Exception as error:  # Capture the real Oracle exception for assertion below.
                    second.rollback()
                    result.append(error)

            worker = threading.Thread(target=insert_competing_slot, daemon=True)
            worker.start()
            self.assertTrue(started.wait(timeout=5), "second Oracle session did not start")
            # Give the second session time to enter Oracle while the duplicate key is uncommitted.
            time.sleep(0.25)
            first.commit()
            worker.join(timeout=20)
            self.assertFalse(worker.is_alive(), "Oracle did not resolve the duplicate-key wait")
            self.assertEqual(len(result), 1)
            self.assertIsInstance(result[0], oracledb.Error, result)
            self.assertIn("ORA-00001", str(result[0]))
        finally:
            try:
                first.rollback()
                second.rollback()
            finally:
                first.close()
                second.close()


if __name__ == "__main__":
    unittest.main()
