"""Opt-in real Oracle role workflows. NEVER a SQLite fallback.

Requires007+008+09+11, the exact disposable schema, both integration switches and ack.
Creates unique synthetic records and retains their clinical/financial history.
No drop/delete/guard-disabling cleanup. This suite has NOT run in this environment.
"""

import os
import re
import secrets
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

from hms import create_app
from hms.api import hospital_today
from hms.database import OracleDatabase
from tests.test_oracle_integration import TEST_ACK, _validate_test_schema_identity


@unittest.skipUnless(
    os.getenv("HMS_ORACLE_INTEGRATION") == "1"
    and os.getenv("HMS_MULTIUSER_ORACLE_INTEGRATION") == "1"
    and os.getenv("HMS_ORACLE_TEST_ACK") == TEST_ACK,
    "Multi-user Oracle tests require both integration switches and exact disposable-schema acknowledgement.",
)
class MultiuserOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        _validate_test_schema_identity(os.getenv("ORACLE_USER"))
        cls.db = OracleDatabase.from_environment()
        if not cls.db.configured:
            raise RuntimeError("Enabled live test requires configured Oracle.")
        with cls.db.connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "SELECT SYS_CONTEXT('USERENV','SESSION_USER'),SYS_CONTEXT('USERENV','CURRENT_SCHEMA') FROM dual"
                )
                _validate_test_schema_identity(os.getenv("ORACLE_USER"), *c.fetchone())
                c.execute(
                    "SELECT schema_version,multiuser_version,correction_version FROM HMS_Settings WHERE singleton=1"
                )
                if tuple(int(v) for v in c.fetchone()) != (6, 1, 1):
                    raise RuntimeError("Complete007/008 and postflights09/11 first.")
                c.execute("SELECT COUNT(*) FROM HMS_User")
                empty = c.fetchone()[0] == 0
        cls.app = create_app(
            database=cls.db,
            test_config={
                "TESTING": True,
                "AUTH_REQUIRED": True,
                "DEMO_USERNAME": "",
                "DEMO_PASSWORD": "",
            },
        )
        if empty:
            result = cls.app.test_cli_runner().invoke(
                args=[
                    "init-manager",
                    "--username",
                    "oracle.bootstrap." + secrets.token_hex(3),
                    "--password",
                    secrets.token_urlsafe(24),
                ]
            )
            if result.exit_code:
                raise RuntimeError("Disposable bootstrap failed; inspect local schema.")

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.tag = uuid.uuid4().hex[:10]
        self.clients = {}
        self.csrf = {}
        self.identities = {}
        result = self.app.test_cli_runner().invoke(
            args=["create-demo-accounts", "--ack", "SYNTHETIC_ONLY"]
        )
        self.assertEqual(result.exit_code, 0, str(result.exception))
        self.credentials = {
            name.split(".")[0]: (name, password)
            for name, password in (
                line.split("\t") for line in result.output.strip().splitlines()
            )
        }
        with self.app.app_context():
            self.today = hospital_today()
        for role in self.credentials:
            self.client(role)

    def client(self, role, new=False):
        if new or role not in self.clients:
            c = self.app.test_client()
            name, password = self.credentials[role]
            r = c.post("/api/auth/login", json={"username": name, "password": password})
            self.assertEqual(r.status_code, 200, r.get_json())
            identity = c.get("/api/auth/me").get_json()["data"]
            if new:
                return c, identity["csrf_token"]
            self.clients[role] = c
            self.csrf[role] = identity["csrf_token"]
            self.identities[role] = identity
        return self.clients[role]

    def write(self, role, path, body, method="post"):
        return getattr(self.client(role), method)(
            path, json=body, headers={"X-CSRF-Token": self.csrf[role]}
        )

    def save(self, response):
        self.assertIn(response.status_code, (200, 201), response.get_json())
        return response.get_json()["data"].get("id")

    def action(self, role, name, body):
        if name == "receive_batch":
            body = {"idempotency_key": str(uuid.uuid4()), **body}
        return self.write(role, "/api/work/" + name, body)

    def outpatient(self, quantity=2):
        self.pid = self.identities["patient"]["patient_id"]
        self.did = self.identities["doctor"]["doctor_id"]
        aid = self.save(
            self.write(
                "receptionist",
                "/api/appointments",
                {
                    "patient_id": self.pid,
                    "doctor_id": self.did,
                    "appointment_date": self.today.isoformat(),
                    "appointment_time": "09:00",
                    "duration_minutes": 30,
                },
            )
        )
        for status in ("Checked In", "Waiting"):
            self.save(
                self.write(
                    "receptionist",
                    f"/api/appointments/{aid}",
                    {"status": status},
                    "put",
                )
            )
        self.eid = self.save(
            self.action(
                "doctor",
                "consultation",
                {
                    "patient_id": self.pid,
                    "appointment_id": aid,
                    "diagnosis": "Synthetic working diagnosis",
                },
            )
        )
        self.med = self.save(
            self.write(
                "pharmacist",
                "/api/medicines",
                {
                    "medicine_name": "Oracle role " + self.tag,
                    "manufacturer": "Synthetic",
                    "price": "5.00",
                    "stock_quantity": 0,
                },
            )
        )
        self.rx = self.save(
            self.action(
                "doctor",
                "prescribe",
                {
                    "encounter_id": self.eid,
                    "medicine_id": self.med,
                    "ordered_quantity": quantity,
                    "dosage": "Synthetic units",
                    "duration": "Synthetic days",
                },
            )
        )
        self.batch = self.save(
            self.action(
                "pharmacist",
                "receive_batch",
                {
                    "medicine_id": self.med,
                    "batch_number": self.tag,
                    "expires_on": (self.today + timedelta(days=30)).isoformat(),
                    "quantity": quantity,
                },
            )
        )

    def test_new_objects_compile_and_personal_sessions_scope_all_roles(self):
        with self.db.connection() as conn:
            with conn.cursor() as c:
                c.execute("SELECT COUNT(*) FROM user_objects WHERE status='INVALID'")
                self.assertEqual(c.fetchone()[0], 0)
                expected = {
                    x.upper()
                    for x in re.findall(
                        r"CREATE OR REPLACE TRIGGER (\w+)",
                        Path("sql/migrations/007_multiuser.sql").read_text(),
                    )
                }
                c.execute(
                    "SELECT trigger_name FROM user_triggers WHERE status='ENABLED'"
                )
                self.assertTrue(expected <= {r[0] for r in c.fetchall()})
        for role, client in self.clients.items():
            self.assertEqual(client.get("/api/workspace").status_code, 200)
            if role != "manager":
                self.assertEqual(client.get("/api/admin/users").status_code, 403)
        other = self.save(
            self.write(
                "manager",
                "/api/patients",
                {
                    "patient_name": "Unassigned " + self.tag,
                    "date_of_birth": "2000-01-01",
                    "gender": "O",
                },
            )
        )
        self.assertEqual(
            self.client("patient").get(f"/api/patients/{other}/summary").status_code,
            404,
        )

    def test_live_outpatient_result_dispense_bill_payment_and_followup(self):
        self.outpatient()
        tid = self.save(
            self.action(
                "manager",
                "test_catalog",
                {"test_name": "Role test " + self.tag, "fee": "30.00"},
            )
        )
        order = self.save(
            self.action(
                "doctor", "order_test", {"encounter_id": self.eid, "test_id": tid}
            )
        )
        self.save(
            self.action(
                "lab", "result", {"order_id": order, "result_text": "Synthetic result"}
            )
        )
        request = {
            "prescription_id": self.rx,
            "batch_id": self.batch,
            "quantity": 2,
            "idempotency_key": str(uuid.uuid4()),
        }
        first = self.save(self.action("pharmacist", "dispense", request))
        self.assertEqual(
            self.save(self.action("pharmacist", "dispense", request)), first
        )
        self.save(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": self.eid,
                    "diagnosis": "Synthetic final",
                    "clinical_notes": "Synthetic released note",
                },
            )
        )
        bill = self.save(
            self.action("cashier", "prepare_bill", {"encounter_id": self.eid})
        )
        ledger = (
            self.client("cashier").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        payment = {
            "amount": ledger["balance"],
            "payment_method": "Cash",
            "reference": "Synthetic " + self.tag,
            "idempotency_key": str(uuid.uuid4()),
        }
        first = self.save(self.write("cashier", f"/api/bills/{bill}/payments", payment))
        self.assertEqual(
            self.save(self.write("cashier", f"/api/bills/{bill}/payments", payment)),
            first,
        )
        self.assertEqual(
            self.client("patient")
            .get(f"/api/bills/{bill}/ledger")
            .get_json()["data"]["balance"],
            "0.00",
        )
        self.save(
            self.action(
                "patient",
                "request_appointment",
                {
                    "doctor_id": self.did,
                    "encounter_id": self.eid,
                    "requested_date": (self.today + timedelta(days=1)).isoformat(),
                    "requested_time": "10:00",
                    "reason": "Synthetic followup",
                },
            )
        )

    def test_live_two_dispensing_requests_cannot_overdraw_order_or_stock(self):
        self.outpatient()
        parties = [self.client("pharmacist", new=True) for _ in range(2)]

        def dispense(party):
            client, csrf = party
            return client.post(
                "/api/work/dispense",
                json={
                    "prescription_id": self.rx,
                    "batch_id": self.batch,
                    "quantity": 2,
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"X-CSRF-Token": csrf},
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(dispense, parties))
        self.assertEqual(sorted(statuses), [201, 409])
        with self.db.connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "SELECT stock_quantity FROM Medicine WHERE medicine_id=:id",
                    {"id": self.med},
                )
                self.assertEqual(c.fetchone()[0], 0)
                c.execute(
                    "SELECT SUM(quantity) FROM HMS_Dispense WHERE prescription_id=:id",
                    {"id": self.rx},
                )
                self.assertEqual(c.fetchone()[0], 2)

    def test_live_ward_assignment_transfer_discharge_final_invoice(self):
        pid = self.identities["patient"]["patient_id"]
        did = self.identities["doctor"]["doctor_id"]
        rooms = [
            self.save(
                self.write(
                    "manager",
                    "/api/rooms",
                    {"room_number": self.tag + str(i), "room_type": "Synthetic"},
                )
            )
            for i in range(2)
        ]
        admission = self.save(
            self.write(
                "receptionist",
                "/api/admissions",
                {
                    "patient_id": pid,
                    "room_id": rooms[0],
                    "admission_date": self.today.isoformat(),
                },
            )
        )
        self.save(
            self.action(
                "manager",
                "assign_ward",
                {
                    "admission_id": admission,
                    "user_id": self.identities["nurse"]["user_id"],
                },
            )
        )
        self.save(
            self.action(
                "manager", "assign_doctor", {"patient_id": pid, "doctor_id": did}
            )
        )
        self.save(
            self.action(
                "nurse",
                "observation",
                {
                    "admission_id": admission,
                    "observation": "Synthetic ward observation",
                },
            )
        )
        eid = self.save(
            self.action(
                "doctor", "consultation", {"patient_id": pid, "admission_id": admission}
            )
        )
        self.assertEqual(
            self.write(
                "nurse",
                f"/api/admissions/{admission}/discharge",
                {"discharge_date": self.today.isoformat()},
            ).status_code,
            409,
        )
        self.save(
            self.write(
                "nurse", f"/api/admissions/{admission}", {"room_id": rooms[1]}, "put"
            )
        )
        self.save(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": eid,
                    "diagnosis": "Synthetic ward review",
                    "clinical_notes": "Synthetic discharge note",
                },
            )
        )
        self.save(
            self.write(
                "nurse",
                f"/api/admissions/{admission}/discharge",
                {"discharge_date": self.today.isoformat()},
            )
        )
        history = (
            self.client("patient")
            .get(f"/api/patients/{pid}/room-history")
            .get_json()["data"]
        )
        self.assertEqual(len(history), 2)
        bill = self.save(
            self.action(
                "cashier",
                "prepare_bill",
                {"admission_id": admission, "room_charge": "100.00"},
            )
        )
        ledger = (
            self.client("cashier").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.save(
            self.write(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": ledger["balance"],
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        self.assertEqual(
            self.client("patient")
            .get(f"/api/bills/{bill}/ledger")
            .get_json()["data"]["balance"],
            "0.00",
        )

    def correction(self, role, action, **body):
        body.setdefault("idempotency_key", str(uuid.uuid4()))
        return self.write(role, "/api/corrections/" + action, body)

    def test_live_corrections_retain_clinical_cash_and_stock_facts(self):
        self.outpatient(quantity=2)
        dispense = self.save(
            self.action(
                "pharmacist",
                "dispense",
                {
                    "prescription_id": self.rx,
                    "batch_id": self.batch,
                    "quantity": 1,
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        self.save(
            self.correction(
                "doctor",
                "cancel_rx",
                prescription_id=self.rx,
                reason="Synthetic changed treatment",
            )
        )
        catalog = self.save(
            self.action(
                "manager",
                "test_catalog",
                {"test_name": "Correction test " + self.tag, "fee": "5.00"},
            )
        )
        cancelled = self.save(
            self.action(
                "doctor", "order_test", {"encounter_id": self.eid, "test_id": catalog}
            )
        )
        self.save(
            self.correction(
                "doctor",
                "cancel_test",
                order_id=cancelled,
                reason="Synthetic not indicated",
            )
        )
        self.assertEqual(
            self.action(
                "lab",
                "result",
                {"order_id": cancelled, "result_text": "Must be rejected"},
            ).status_code,
            409,
        )
        self.save(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": self.eid,
                    "diagnosis": "Synthetic original",
                    "clinical_notes": "Synthetic original note",
                },
            )
        )
        self.save(
            self.correction(
                "doctor",
                "amend_consultation",
                encounter_id=self.eid,
                content="Synthetic explanatory appendix",
                reason="Synthetic transcription clarification",
            )
        )
        bill = self.save(
            self.action("cashier", "prepare_bill", {"encounter_id": self.eid})
        )
        ledger = (
            self.client("cashier").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        payment = self.save(
            self.write(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": ledger["balance"],
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        returned = self.save(
            self.correction(
                "pharmacist",
                "return_stock",
                dispense_id=dispense,
                quantity=1,
                disposition="Restock",
                reason="Synthetic sealed verified return",
            )
        )
        body = dict(
            bill_id=bill,
            payment_id=payment,
            stock_event_id=returned,
            amount="5.00",
            reason="Synthetic original-price return",
            idempotency_key=str(uuid.uuid4()),
        )
        refund = self.save(self.correction("cashier", "refund", **body))
        self.assertEqual(
            self.save(self.correction("cashier", "refund", **body)), refund
        )
        self.save(
            self.correction(
                "pharmacist",
                "write_off",
                batch_id=self.batch,
                quantity=1,
                reason="Synthetic damaged package",
            )
        )
        with self.db.connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "SELECT clinical_notes FROM HMS_Encounter WHERE encounter_id=:id",
                    {"id": self.eid},
                )
                self.assertEqual(c.fetchone()[0], "Synthetic original note")
                c.execute(
                    "SELECT amount FROM Bill_Payment WHERE payment_id=:id",
                    {"id": payment},
                )
                self.assertEqual(
                    Decimal(str(c.fetchone()[0])),
                    Decimal(ledger["balance"]),
                )
                c.execute(
                    "SELECT difference FROM V_HMS_Batch_Recon WHERE batch_id=:id",
                    {"id": self.batch},
                )
                self.assertEqual(c.fetchone()[0], 0)
                c.execute(
                    "SELECT difference FROM V_HMS_Medicine_Recon WHERE medicine_id=:id",
                    {"id": self.med},
                )
                self.assertEqual(c.fetchone()[0], 0)
        ledger = (
            self.client("patient").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertEqual(ledger["balance"], "0.00")
        self.assertEqual(len(ledger["corrections"]), 2)

    def test_live_refund_race_and_corrective_history_guards(self):
        bill = self.save(
            self.write(
                "cashier",
                "/api/bills",
                {
                    "patient_id": self.identities["patient"]["patient_id"],
                    "bill_date": self.today.isoformat(),
                    "consultation_charge": "100",
                    "room_charge": "0",
                    "medicine_charge": "0",
                },
            )
        )
        pay = self.save(
            self.write(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "100",
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        actors = [self.client("manager", new=True) for _ in range(2)]

        def refund(actor):
            client, csrf = actor
            return client.post(
                "/api/corrections/refund",
                json={
                    "bill_id": bill,
                    "payment_id": pay,
                    "amount": "75",
                    "reason": "Synthetic concurrent correction",
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"X-CSRF-Token": csrf},
            ).status_code

        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(refund, actors)), [201, 409])
        import oracledb

        with self.db.connection() as conn:
            with conn.cursor() as c:
                with self.assertRaises(oracledb.DatabaseError) as failure:
                    c.execute(
                        "UPDATE HMS_Fin_Event SET reason='Forbidden rewrite' WHERE bill_id=:id",
                        {"id": bill},
                    )
                self.assertIn("ORA-20211", str(failure.exception))
            conn.rollback()
        self.assertEqual(
            self.client("patient")
            .get(f"/api/bills/{bill}/ledger")
            .get_json()["data"]["refunds"],
            "75.00",
        )

    def test_live_correction_metadata_and_atomic_rollback(self):
        with self.db.connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "SELECT COUNT(*) FROM user_triggers WHERE trigger_name LIKE 'TRG_CC_%' AND status='ENABLED'"
                )
                self.assertEqual(c.fetchone()[0], 22)
                c.execute("SELECT COUNT(*) FROM user_objects WHERE status='INVALID'")
                self.assertEqual(c.fetchone()[0], 0)
        bill = self.save(
            self.write(
                "cashier",
                "/api/bills",
                {
                    "patient_id": self.identities["patient"]["patient_id"],
                    "bill_date": self.today.isoformat(),
                    "consultation_charge": "100",
                    "room_charge": "0",
                    "medicine_charge": "0",
                },
            )
        )
        pay = self.save(
            self.write(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "100",
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        from unittest.mock import patch

        with patch(
            "hms.corrections.audit",
            side_effect=RuntimeError("Synthetic rollback injection"),
        ):
            with self.assertLogs(self.app.logger, level="ERROR"):
                self.assertEqual(
                    self.correction(
                        "manager",
                        "refund",
                        bill_id=bill,
                        payment_id=pay,
                        amount="10",
                        reason="Synthetic atomic rollback",
                    ).status_code,
                    500,
                )
        self.db.close()  # Reopen real pool: committed receipt survives, rolled-back events do not.
        data = (
            self.client("patient").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertEqual(data["corrections"], [])
        self.assertEqual(data["paid"], "100.00")
