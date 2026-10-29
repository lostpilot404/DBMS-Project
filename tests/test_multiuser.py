"""Role/session regressions. SQLite compatibility fixture != live Oracle."""

import importlib.util
import unittest
from pathlib import Path

from hms import create_app
from tests.test_app import FakeDatabase


class MultiuserDiscoveryTests(unittest.TestCase):
    def test_default_private_api_requires_personal_login(self):
        c = create_app(
            database=FakeDatabase(), test_config={"TESTING": True}
        ).test_client()
        self.assertEqual(c.get("/api/patients").status_code, 401)

    def test_auth_module_is_implemented(self):
        self.assertIsNotNone(importlib.util.find_spec("hms.auth"))

    def test_additive_identity_migration_exists(self):
        self.assertTrue(Path("sql/migrations/007_multiuser.sql").exists())


import uuid
from datetime import timedelta

from hms.auth import ROLES
from tests.role_fixture import RoleDatabase


class RoleFixtureMixin:
    def setUp(self):
        self.db = RoleDatabase()
        self.app = create_app(database=self.db, test_config={"TESTING": True})
        self.clients = {}
        self.csrf = {}

    def client(self, role):
        if role not in self.clients:
            c = self.app.test_client()
            r = c.post(
                "/api/auth/login",
                json={"username": role, "password": "fixture-password-only"},
            )
            self.assertEqual(r.status_code, 200, r.get_json())
            self.clients[role] = c
            self.csrf[role] = r.get_json()["data"]["csrf_token"]
        return self.clients[role]

    def post(self, role, path, body):
        c = self.client(role)
        return c.post(path, json=body, headers={"X-CSRF-Token": self.csrf[role]})

    def action(self, role, action, body):
        if action=='receive_batch':body={'idempotency_key':str(uuid.uuid4()),**body}
        return self.post(role, "/api/work/" + action, body)

    def saved(self, r):
        self.assertIn(r.status_code, (200, 201), r.get_json())
        return r.get_json()["data"]["id"]


class RoleWorkflowTests(RoleFixtureMixin, unittest.TestCase):
    def test_every_role_logs_in_and_has_only_its_workspace(self):
        for role in ROLES:
            with self.subTest(role=role):
                c = self.client(role)
                r = c.get("/api/workspace")
                self.assertEqual(r.status_code, 200, r.get_json())
                self.assertEqual(r.get_json()["data"]["role"], role)
                self.assertNotIn("password_hash", str(c.get("/api/auth/me").get_json()))

    def test_direct_api_and_id_manipulation_are_blocked(self):
        patient = self.client("patient")
        for path in [
            "/api/patients/2",
            "/api/patients/2/summary",
            "/api/details/bills/99",
        ]:
            self.assertIn(patient.get(path).status_code, (403, 404))
        for role in ROLES[1:]:
            self.assertEqual(self.client(role).get("/api/admin/users").status_code, 403)
            self.assertEqual(
                self.post(role, "/api/admin/users", {"role": "manager"}).status_code,
                403,
            )
        self.assertEqual(
            self.client("maintenance").get("/api/patients").status_code, 403
        )
        self.assertEqual(
            self.client("patient").get("/api/details/doctors/1").status_code, 403
        )
        self.assertEqual(
            self.client("pharmacist").get("/api/details/medicines/1").status_code, 403
        )
        self.assertEqual(
            self.client("nurse").get("/api/details/rooms/1").status_code, 403
        )
        rows = patient.get("/api/patients").get_json()["data"]
        self.assertEqual([r["patient_id"] for r in rows], [1])

    def test_csrf_logout_deactivation_and_session_rotation(self):
        c = self.client("patient")
        cookie = c.get_cookie("hms_session")
        self.assertTrue(cookie.http_only)
        self.assertEqual(c.post("/api/auth/logout", json={}).status_code, 403)
        self.assertEqual(self.post("patient", "/api/auth/logout", {}).status_code, 200)
        self.assertEqual(c.get("/api/auth/me").status_code, 401)
        self.clients.pop("patient")
        c = self.client("patient")
        self.assertNotEqual(c.get_cookie("hms_session").value, cookie.value)
        self.db.sql.execute(
            "UPDATE HMS_User SET is_active='N' WHERE username='patient'"
        )
        self.db.sql.commit()
        self.assertEqual(c.get("/api/auth/me").status_code, 401)

    def test_login_throttle_and_password_hash(self):
        c = self.app.test_client()
        for _ in range(8):
            self.assertEqual(
                c.post(
                    "/api/auth/login",
                    json={"username": "patient", "password": "incorrect"},
                ).status_code,
                401,
            )
        self.assertEqual(
            c.post(
                "/api/auth/login", json={"username": "patient", "password": "incorrect"}
            ).status_code,
            429,
        )
        encoded = self.db.sql.execute(
            "SELECT password_hash FROM HMS_User WHERE username='patient'"
        ).fetchone()[0]
        self.assertTrue(encoded.startswith("scrypt:"))

    def test_manager_account_creation_role_links_and_last_manager(self):
        c = self.client("manager")
        r = c.put(
            "/api/admin/users/1",
            json={"is_active": "N"},
            headers={"X-CSRF-Token": self.csrf["manager"]},
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(
            self.post(
                "manager",
                "/api/admin/users",
                {
                    "username": "bad",
                    "password": "short",
                    "role": "patient",
                    "patient_id": 1,
                },
            ).status_code,
            400,
        )
        sid = self.saved(
            self.action(
                "manager",
                "staff",
                {"full_name": "Extra Reception", "staff_kind": "receptionist"},
            )
        )
        self.saved(
            self.post(
                "manager",
                "/api/admin/users",
                {
                    "username": "extra.reception",
                    "password": "a-unique-long-password",
                    "role": "receptionist",
                    "staff_id": sid,
                },
            )
        )

    def test_outpatient_cross_role_workflow_persists_and_reconciles(self):
        from hms.api import hospital_today

        day = hospital_today().isoformat()
        rid = self.saved(
            self.action(
                "patient",
                "request_appointment",
                {
                    "patient_id": 2,
                    "doctor_id": 1,
                    "requested_date": day,
                    "requested_time": "09:00",
                    "reason": "Synthetic visit",
                },
            )
        )
        self.assertEqual(
            self.db.sql.execute(
                "SELECT patient_id FROM HMS_Appointment_Request WHERE request_id=?",
                (rid,),
            ).fetchone()[0],
            1,
        )
        aid = self.saved(
            self.action(
                "receptionist",
                "review_request",
                {"request_id": rid, "decision": "Accepted"},
            )
        )
        c = self.client("receptionist")
        for status in ["Checked In", "Waiting"]:
            r = c.put(
                f"/api/appointments/{aid}",
                json={"status": status},
                headers={"X-CSRF-Token": self.csrf["receptionist"]},
            )
            self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(
            c.put(
                f"/api/appointments/{aid}",
                json={"status": "Completed"},
                headers={"X-CSRF-Token": self.csrf["receptionist"]},
            ).status_code,
            403,
        )
        eid = self.saved(
            self.action(
                "doctor",
                "consultation",
                {
                    "patient_id": 1,
                    "appointment_id": aid,
                    "diagnosis": "Synthetic diagnosis",
                    "clinical_notes": "Clinical test note",
                },
            )
        )
        self.assertEqual(
            self.client("doctor2").get("/api/appointments/" + str(aid)).status_code, 404
        )
        self.assertEqual(
            self.action(
                "doctor2",
                "complete_consultation",
                {
                    "encounter_id": eid,
                    "diagnosis": "forged",
                    "clinical_notes": "forged",
                },
            ).status_code,
            404,
        )
        rx = self.saved(
            self.action(
                "doctor",
                "prescribe",
                {
                    "encounter_id": eid,
                    "medicine_id": 1,
                    "ordered_quantity": 2,
                    "dosage": "One",
                    "duration": "Two days",
                },
            )
        )
        oid = self.saved(
            self.action("doctor", "order_test", {"encounter_id": eid, "test_id": 1})
        )
        self.saved(
            self.action(
                "lab",
                "result",
                {"order_id": oid, "result_text": "Synthetic normal result"},
            )
        )
        batch = self.saved(
            self.action(
                "pharmacist",
                "receive_batch",
                {
                    "medicine_id": 1,
                    "batch_number": "B1",
                    "expires_on": (hospital_today() + timedelta(days=60)).isoformat(),
                    "quantity": 10,
                },
            )
        )
        dispense = {
            "prescription_id": rx,
            "batch_id": batch,
            "quantity": 2,
            "idempotency_key": str(uuid.uuid4()),
        }
        did = self.saved(self.action("pharmacist", "dispense", dispense))
        self.assertEqual(
            self.saved(self.action("pharmacist", "dispense", dispense)), did
        )
        self.assertEqual(
            self.db.sql.execute(
                "SELECT stock_quantity FROM Medicine WHERE medicine_id=1"
            ).fetchone()[0],
            8,
        )
        self.saved(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": eid,
                    "diagnosis": "Synthetic diagnosis",
                    "clinical_notes": "Final synthetic note",
                },
            )
        )
        bill = self.saved(self.action("cashier", "prepare_bill", {"encounter_id": eid}))
        ledger = (
            self.client("cashier").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertEqual(ledger["billed"], "60.00")
        self.assertEqual(len(ledger["items"]), 3)
        pay = {
            "amount": "60.00",
            "payment_method": "Cash",
            "idempotency_key": str(uuid.uuid4()),
        }
        receipt = self.saved(self.post("cashier", f"/api/bills/{bill}/payments", pay))
        self.assertEqual(
            self.saved(self.post("cashier", f"/api/bills/{bill}/payments", pay)),
            receipt,
        )
        own = self.client("patient").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        self.assertEqual((own["status"], own["balance"]), ("Paid", "0.00"))
        self.assertEqual(
            self.client("patient2").get(f"/api/bills/{bill}/ledger").status_code, 404
        )
        self.assertEqual(
            self.client("patient2").get("/api/details/bills/" + str(bill)).status_code,
            404,
        )
        self.assertEqual(
            self.action("cashier", "prepare_bill", {"encounter_id": eid}).status_code,
            409,
        )
        self.saved(
            self.action(
                "doctor",
                "request_appointment",
                {
                    "patient_id": 1,
                    "encounter_id": eid,
                    "requested_date": (
                        hospital_today() + timedelta(days=7)
                    ).isoformat(),
                    "requested_time": "10:00",
                    "reason": "Follow up",
                },
            )
        )
        workspace = self.client("patient").get("/api/workspace").get_json()["data"]
        self.assertEqual(
            workspace["queues"]["tests"][0]["result_text"], "Synthetic normal result"
        )

    def test_inpatient_assignment_observation_transfer_discharge_final_bill(self):
        from hms.api import hospital_today

        day = hospital_today().isoformat()
        aid = self.saved(
            self.post(
                "manager",
                "/api/admissions",
                {"patient_id": 1, "room_id": 1, "admission_date": day},
            )
        )
        self.assertEqual(
            self.action(
                "nurse", "observation", {"admission_id": aid, "observation": "forged"}
            ).status_code,
            404,
        )
        self.saved(
            self.action("manager", "assign_ward", {"admission_id": aid, "user_id": 5})
        )
        self.saved(
            self.action("manager", "assign_doctor", {"patient_id": 1, "doctor_id": 1})
        )
        self.saved(
            self.action(
                "nurse",
                "observation",
                {"admission_id": aid, "observation": "Synthetic ward observation"},
            )
        )
        eid = self.saved(
            self.action(
                "doctor",
                "consultation",
                {
                    "patient_id": 1,
                    "admission_id": aid,
                    "diagnosis": "Ward care",
                    "clinical_notes": "Synthetic",
                },
            )
        )
        c = self.client("nurse")
        r = c.put(
            f"/api/admissions/{aid}",
            json={"room_id": 2},
            headers={"X-CSRF-Token": self.csrf["nurse"]},
        )
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertEqual(
            self.db.sql.execute(
                "SELECT COUNT(*) FROM Admission_Room_Stay WHERE admission_id=?", (aid,)
            ).fetchone()[0],
            2,
        )
        self.saved(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": eid,
                    "diagnosis": "Completed ward care",
                    "clinical_notes": "Synthetic discharge review",
                },
            )
        )
        self.assertEqual(
            self.post(
                "nurse", f"/api/admissions/{aid}/discharge", {"discharge_date": day}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.action(
                "nurse", "observation", {"admission_id": aid, "observation": "late"}
            ).status_code,
            404,
        )
        bill = self.saved(
            self.action(
                "cashier", "prepare_bill", {"admission_id": aid, "room_charge": "100"}
            )
        )
        self.assertEqual(
            self.client("patient")
            .get(f"/api/bills/{bill}/ledger")
            .get_json()["data"]["billed"],
            "120.00",
        )

    def test_forbidden_workflow_matrix_is_server_enforced(self):
        from hms.workflows import ACTIONS

        for role in ROLES:
            for action, allowed in ACTIONS.items():
                if role not in allowed:
                    with self.subTest(role=role, action=action):
                        self.assertEqual(self.action(role, action, {}).status_code, 403)


class AdditionalRoleSecurityTests(RoleFixtureMixin, unittest.TestCase):
    def test_cannot_prepare_unfinished_consultation(self):
        self.db.sql.execute(
            "INSERT INTO HMS_Care_Assignment(patient_id,doctor_id) VALUES(1,1)"
        )
        self.db.sql.execute(
            "INSERT INTO HMS_Encounter(encounter_id,patient_id,doctor_id,status) VALUES(1,1,1,'Open')"
        )
        self.db.sql.execute(
            "INSERT INTO HMS_Care_Charge(encounter_id,source_kind,source_id,description,quantity,unit_price) VALUES(1,'Consultation',1,'Visit',1,20)"
        )
        self.db.sql.commit()
        self.assertEqual(
            self.action("cashier", "prepare_bill", {"encounter_id": 1}).status_code, 409
        )

    def test_expired_session_and_nonclinical_workspace(self):
        self.client("patient")
        self.db.sql.execute(
            "UPDATE HMS_Session SET expires_at='2000-01-01' WHERE user_id=3"
        )
        self.db.sql.commit()
        self.assertEqual(self.clients["patient"].get("/api/auth/me").status_code, 401)
        payload = self.client("maintenance").get("/api/workspace").get_json()["data"]
        self.assertNotIn("Patient One", str(payload))

    def test_local_initial_manager_and_separate_generated_demo_credentials(self):
        db = RoleDatabase(seed=False)
        app = create_app(database=db, test_config={"TESTING": True})
        runner = app.test_cli_runner()
        result = runner.invoke(
            args=[
                "init-manager",
                "--username",
                "first.manager",
                "--password",
                "fixture-bootstrap-password",
            ]
        )
        self.assertEqual(result.exit_code, 0, str(result.exception))
        result = runner.invoke(
            args=[
                "init-manager",
                "--username",
                "another.manager",
                "--password",
                "fixture-bootstrap-password",
            ]
        )
        self.assertNotEqual(result.exit_code, 0)
        result = runner.invoke(args=["create-demo-accounts", "--ack", "SYNTHETIC_ONLY"])
        self.assertEqual(result.exit_code, 0, str(result.exception))
        pairs = [line.split("\t") for line in result.output.strip().splitlines()]
        self.assertEqual(len(pairs), 9)
        self.assertEqual(len({p[1] for p in pairs}), 9)


class StaffAndStockTests(RoleFixtureMixin, unittest.TestCase):
    def test_manager_can_edit_staff_and_deactivation_revokes_access(self):
        self.client("receptionist")
        r = self.action(
            "manager",
            "update_staff",
            {"staff_id": 4, "full_name": "Updated Reception", "is_active": "N"},
        )
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual(
            self.clients["receptionist"].get("/api/auth/me").status_code, 401
        )
        self.assertEqual(
            self.action(
                "manager", "update_staff", {"staff_id": 1, "is_active": "N"}
            ).status_code,
            409,
        )

    def test_expired_and_overlarge_dispensing_has_no_stock_side_effect(self):

        self.db.sql.execute(
            "INSERT INTO HMS_Encounter(encounter_id,patient_id,doctor_id) VALUES(1,1,1)"
        )
        self.db.sql.execute(
            "INSERT INTO Prescription(prescription_id,patient_id,doctor_id,medicine_id,encounter_id,ordered_quantity) VALUES(1,1,1,1,1,2)"
        )
        self.db.sql.execute(
            "INSERT INTO HMS_Medicine_Batch VALUES(1,1,'Expired','2000-01-01',10)"
        )
        self.db.sql.execute("UPDATE Medicine SET stock_quantity=10 WHERE medicine_id=1")
        self.db.sql.commit()
        self.assertEqual(
            self.action(
                "pharmacist",
                "dispense",
                {
                    "prescription_id": 1,
                    "batch_id": 1,
                    "quantity": 2,
                    "idempotency_key": str(uuid.uuid4()),
                },
            ).status_code,
            409,
        )
        self.assertEqual(
            self.db.sql.execute("SELECT stock_quantity FROM Medicine").fetchone()[0], 10
        )
        self.db.sql.execute("UPDATE HMS_Medicine_Batch SET expires_on='2099-01-01'")
        self.db.sql.commit()
        self.assertEqual(
            self.action(
                "pharmacist",
                "dispense",
                {
                    "prescription_id": 1,
                    "batch_id": 1,
                    "quantity": 3,
                    "idempotency_key": str(uuid.uuid4()),
                },
            ).status_code,
            409,
        )
        from unittest.mock import patch

        from hms.api import ApiError

        with patch(
            "hms.workflows.care_charge",
            side_effect=ApiError("Injected post-stock failure", 409, "injected"),
        ):
            self.assertEqual(
                self.action(
                    "pharmacist",
                    "dispense",
                    {
                        "prescription_id": 1,
                        "batch_id": 1,
                        "quantity": 2,
                        "idempotency_key": str(uuid.uuid4()),
                    },
                ).status_code,
                409,
            )
        self.assertEqual(
            self.db.sql.execute("SELECT quantity FROM HMS_Medicine_Batch").fetchone()[
                0
            ],
            10,
        )
        self.assertEqual(
            self.db.sql.execute("SELECT stock_quantity FROM Medicine").fetchone()[0], 10
        )
        self.assertEqual(
            self.db.sql.execute("SELECT COUNT(*) FROM HMS_Dispense").fetchone()[0], 0
        )

    def test_password_change_revokes_all_sessions(self):
        c = self.client("patient")
        other = self.app.test_client()
        other.post(
            "/api/auth/login",
            json={"username": "patient", "password": "fixture-password-only"},
        )
        self.assertEqual(
            self.post(
                "patient",
                "/api/auth/password",
                {
                    "current_password": "fixture-password-only",
                    "new_password": "changed-fixture-password",
                },
            ).status_code,
            200,
        )
        self.assertEqual(c.get("/api/auth/me").status_code, 401)
        self.assertEqual(other.get("/api/auth/me").status_code, 401)

    def test_reception_cannot_reach_clinical_chart_via_generic_details(self):
        self.assertEqual(
            self.client("receptionist").get("/api/details/patients/1").status_code, 403
        )

    def test_doctor_cannot_skip_encounter_using_legacy_status_put(self):
        self.db.sql.execute(
            "INSERT INTO Appointment VALUES(1,1,1,HMS_Today(),'09:00',30,'Waiting')"
        )
        self.db.sql.commit()
        c = self.client("doctor")
        r = c.put(
            "/api/appointments/1",
            json={"status": "In Consultation"},
            headers={"X-CSRF-Token": self.csrf["doctor"]},
        )
        self.assertEqual(r.status_code, 403)

    def test_nurse_cannot_reassign_admission_patient(self):
        self.db.sql.execute("INSERT INTO Admission VALUES(1,1,1,HMS_Today(),NULL)")
        self.db.sql.execute(
            "INSERT INTO HMS_Ward_Assignment(admission_id,user_id) VALUES(1,5)"
        )
        self.db.sql.commit()
        c = self.client("nurse")
        r = c.put(
            "/api/admissions/1",
            json={"patient_id": 2},
            headers={"X-CSRF-Token": self.csrf["nurse"]},
        )
        self.assertEqual(r.status_code, 403)

    def test_patient_chart_includes_released_new_clinical_facts_not_private_drafts(
        self,
    ):
        self.db.sql.execute(
            "INSERT INTO HMS_Encounter(encounter_id,patient_id,doctor_id,diagnosis,clinical_notes) VALUES(1,1,1,'Private working diagnosis','Private draft')"
        )
        self.db.sql.commit()
        first = self.client("patient").get("/api/patients/1/summary").get_json()["data"]
        self.assertIn("consultations", first)
        self.assertEqual(first["consultations"], [])
        self.db.sql.execute(
            "UPDATE HMS_Encounter SET status='Completed',diagnosis='Released diagnosis',clinical_notes='Released note' WHERE encounter_id=1"
        )
        self.db.sql.commit()
        second = (
            self.clients["patient"].get("/api/patients/1/summary").get_json()["data"]
        )
        self.assertEqual(second["consultations"][0]["clinical_notes"], "Released note")
        self.assertTrue(any(e["type"] == "Consultation" for e in second["timeline"]))

    def test_manager_stock_correction_cannot_undercut_known_batches(self):
        self.saved(
            self.action(
                "pharmacist",
                "receive_batch",
                {
                    "medicine_id": 1,
                    "batch_number": "Known",
                    "expires_on": "2099-01-01",
                    "quantity": 10,
                },
            )
        )
        r = self.post("manager", "/api/medicines/1/stock-adjustments", {"change": -1})
        self.assertEqual(r.status_code, 409, r.get_json())

    def test_maintenance_cannot_reserve_an_occupied_room(self):
        task = self.saved(
            self.action(
                "manager",
                "maintenance_request",
                {"room_id": 1, "description": "Synthetic occupied-room check"},
            )
        )
        self.db.sql.execute(
            "UPDATE Room SET availability_status='Occupied' WHERE room_id=1"
        )
        self.db.sql.commit()
        self.assertEqual(
            self.action(
                "maintenance", "maintenance_start", {"task_id": task}
            ).status_code,
            409,
        )

    def test_manager_can_update_or_deactivate_test_catalogue(self):
        self.assertEqual(
            self.action(
                "manager",
                "update_test_catalog",
                {"test_id": 1, "fee": "40.00", "is_active": "N"},
            ).status_code,
            201,
        )
        self.assertEqual(
            str(
                self.db.sql.execute(
                    "SELECT fee FROM HMS_Test_Catalog WHERE test_id=1"
                ).fetchone()[0]
            ),
            "40",
        )
        self.assertEqual(
            self.action(
                "lab", "update_test_catalog", {"test_id": 1, "fee": "0.00"}
            ).status_code,
            403,
        )

    def test_final_inpatient_invoice_requires_an_explicit_agreed_room_fee(self):
        self.db.sql.execute(
            "INSERT INTO Admission VALUES(1,1,1,HMS_Today(),HMS_Today())"
        )
        self.db.sql.execute(
            "INSERT INTO HMS_Encounter(encounter_id,patient_id,doctor_id,admission_id,status) VALUES(1,1,1,1,'Completed')"
        )
        self.db.sql.execute(
            "INSERT INTO HMS_Care_Charge(encounter_id,source_kind,source_id,description,quantity,unit_price) VALUES(1,'Consultation',1,'Synthetic visit',1,20)"
        )
        self.db.sql.commit()
        self.assertEqual(
            self.action("cashier", "prepare_bill", {"admission_id": 1}).status_code, 400
        )

    def test_old_visit_does_not_grant_new_inpatient_clinical_write_assignment(self):
        self.db.sql.execute(
            "INSERT INTO Appointment VALUES(1,1,1,HMS_Today(),'09:00',30,'Completed')"
        )
        self.db.sql.execute("INSERT INTO Admission VALUES(1,1,1,HMS_Today(),NULL)")
        self.db.sql.execute(
            "INSERT INTO HMS_Care_Assignment(patient_id,doctor_id) VALUES(1,2)"
        )
        self.db.sql.commit()
        self.assertEqual(
            self.action(
                "doctor", "consultation", {"patient_id": 1, "admission_id": 1}
            ).status_code,
            403,
        )

    def test_clinician_chart_does_not_bypass_financial_endpoint_policy(self):
        self.db.sql.execute(
            "INSERT INTO HMS_Care_Assignment(patient_id,doctor_id) VALUES(1,1)"
        )
        self.db.sql.execute(
            "INSERT INTO Bill(bill_id,patient_id,bill_date,consultation_charge) VALUES(1,1,HMS_Today(),42)"
        )
        self.db.sql.commit()
        chart = self.client("doctor").get("/api/patients/1/summary").get_json()["data"]
        self.assertEqual(chart.get("bills", []), [])

    def test_inactive_staff_manager_is_not_counted_as_the_last_capable_manager(self):
        sid = self.saved(
            self.action(
                "manager",
                "staff",
                {"full_name": "Inactive manager fixture", "staff_kind": "manager"},
            )
        )
        self.saved(
            self.action("manager", "update_staff", {"staff_id": sid, "is_active": "N"})
        )
        uid = self.saved(
            self.post(
                "manager",
                "/api/admin/users",
                {
                    "username": "inactive.manager",
                    "password": "inactive-fixture-password",
                    "role": "manager",
                    "staff_id": sid,
                },
            )
        )
        headers = {"X-CSRF-Token": self.csrf["manager"]}
        self.assertEqual(
            self.clients["manager"]
            .put(f"/api/admin/users/{uid}", json={"is_active": "N"}, headers=headers)
            .status_code,
            200,
        )
        self.assertEqual(
            self.clients["manager"]
            .put("/api/admin/users/1", json={"is_active": "N"}, headers=headers)
            .status_code,
            409,
        )

    def test_last_manager_cannot_relink_to_an_inactive_staff_identity(self):
        sid = self.saved(
            self.action(
                "manager",
                "staff",
                {"full_name": "Inactive spare manager", "staff_kind": "manager"},
            )
        )
        self.saved(
            self.action("manager", "update_staff", {"staff_id": sid, "is_active": "N"})
        )
        r = self.clients["manager"].put(
            "/api/admin/users/1",
            json={"role": "manager", "staff_id": sid},
            headers={"X-CSRF-Token": self.csrf["manager"]},
        )
        self.assertEqual(r.status_code, 409, r.get_json())


class RuntimePolicyTests(unittest.TestCase):
    def test_auth_bypass_is_restricted_to_test_harnesses(self):
        with self.assertRaises(ValueError):
            create_app(database=FakeDatabase(), test_config={"AUTH_REQUIRED": False})

    def test_secure_remote_personal_auth_does_not_need_shared_basic_credentials(self):
        import os
        import runpy
        from unittest.mock import patch

        with (
            patch.dict(
                os.environ,
                {
                    "HMS_HOST": "0.0.0.0",
                    "HMS_COOKIE_SECURE": "true",
                    "FLASK_DEBUG": "false",
                },
                clear=True,
            ),
            patch("flask.Flask.run") as run,
        ):
            runpy.run_path("app.py", run_name="__main__")
            run.assert_called_once()

    def test_basic_auth_is_not_a_substitute_for_secure_remote_session_cookies(self):
        import os
        import runpy
        from unittest.mock import patch

        with (
            patch.dict(
                os.environ,
                {
                    "HMS_HOST": "0.0.0.0",
                    "HMS_COOKIE_SECURE": "false",
                    "DEMO_USERNAME": "fixture",
                    "DEMO_PASSWORD": "fixture-only",
                    "FLASK_DEBUG": "false",
                },
                clear=True,
            ),
            patch("flask.Flask.run"),
            self.assertRaises(RuntimeError),
        ):
            runpy.run_path("app.py", run_name="__main__")


class AccountAndAssignmentIntegrityTests(RoleFixtureMixin, unittest.TestCase):
    def test_a_second_username_cannot_share_an_existing_personal_patient_link(self):
        r = self.post(
            "manager",
            "/api/admin/users",
            {
                "username": "second.patient",
                "password": "another-fixture-password",
                "role": "patient",
                "patient_id": 1,
            },
        )
        self.assertEqual(r.status_code, 409, r.get_json())

    def test_ward_assignment_requires_an_effectively_active_nurse(self):
        self.db.sql.execute("INSERT INTO Admission VALUES(1,1,1,HMS_Today(),NULL)")
        self.db.sql.commit()
        self.saved(
            self.action("manager", "update_staff", {"staff_id": 5, "is_active": "N"})
        )
        self.assertEqual(
            self.action(
                "manager", "assign_ward", {"admission_id": 1, "user_id": 5}
            ).status_code,
            404,
        )
