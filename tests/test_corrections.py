"""Corrective workflows against persisted SQLite; never Oracle certification."""

import unittest
import uuid

from tests.test_multiuser import RoleFixtureMixin


class CorrectionTests(RoleFixtureMixin, unittest.TestCase):
    def op(self, role, action, **body):
        body.setdefault("idempotency_key", str(uuid.uuid4()))
        return self.post(role, "/api/corrections/" + action, body)

    def clinical(self):
        self.db.sql.execute(
            "INSERT INTO HMS_Care_Assignment(patient_id,doctor_id) VALUES(1,1)"
        )
        self.db.sql.execute("INSERT INTO Admission VALUES(1,1,1,HMS_Today(),NULL)")
        self.db.sql.commit()
        return self.saved(
            self.action(
                "doctor",
                "consultation",
                {"patient_id": 1, "admission_id": 1, "diagnosis": "Original diagnosis"},
            )
        )

    def test_amendment_retains_original_and_rejects_other_doctor(self):
        eid = self.clinical()
        self.saved(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": eid,
                    "diagnosis": "Original",
                    "clinical_notes": "Original note",
                },
            )
        )
        r = self.op(
            "doctor",
            "amend_consultation",
            encounter_id=eid,
            content="Corrected interpretation",
            reason="Transcription error",
        )
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual(
            self.db.sql.execute("SELECT clinical_notes FROM HMS_Encounter").fetchone()[
                0
            ],
            "Original note",
        )
        self.assertEqual(
            self.op(
                "doctor2",
                "amend_consultation",
                encounter_id=eid,
                content="Intrusion",
                reason="Bad",
            ).status_code,
            404,
        )

    def test_cancellations_release_final_billing_without_inventing_service(self):
        eid = self.clinical()
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
        order = self.saved(
            self.action("doctor", "order_test", {"encounter_id": eid, "test_id": 1})
        )
        self.assertEqual(
            self.op(
                "doctor", "cancel_rx", prescription_id=rx, reason="Treatment changed"
            ).status_code,
            201,
        )
        self.assertEqual(
            self.op(
                "doctor", "cancel_test", order_id=order, reason="Not indicated"
            ).status_code,
            201,
        )
        self.saved(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": eid,
                    "diagnosis": "Done",
                    "clinical_notes": "Reviewed",
                },
            )
        )
        bill = self.saved(self.action("cashier", "prepare_bill", {"encounter_id": eid}))
        self.assertEqual(
            self.client("cashier")
            .get(f"/api/bills/{bill}/ledger")
            .get_json()["data"]["billed"],
            "20.00",
        )

    def test_return_writeoff_and_replay_reconcile_stock(self):
        eid = self.clinical()
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
        batch = self.saved(
            self.action(
                "pharmacist",
                "receive_batch",
                {
                    "medicine_id": 1,
                    "batch_number": "R1",
                    "expires_on": "2099-01-01",
                    "quantity": 10,
                },
            )
        )
        disp = self.saved(
            self.action(
                "pharmacist",
                "dispense",
                {
                    "prescription_id": rx,
                    "batch_id": batch,
                    "quantity": 2,
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        body = dict(
            dispense_id=disp,
            quantity=1,
            disposition="Restock",
            reason="Unopened verified return",
            idempotency_key=str(uuid.uuid4()),
        )
        first = self.op("pharmacist", "return_stock", **body)
        self.assertEqual(first.status_code, 201, first.get_json())
        self.assertEqual(self.op("pharmacist", "return_stock", **body).status_code, 200)
        self.assertEqual(
            self.op(
                "pharmacist",
                "write_off",
                batch_id=batch,
                quantity=2,
                reason="Damaged packs",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.db.sql.execute(
                "SELECT stock_quantity FROM Medicine WHERE medicine_id=1"
            ).fetchone()[0],
            7,
        )
        self.assertEqual(
            self.op(
                "pharmacist",
                "return_stock",
                dispense_id=disp,
                quantity=2,
                disposition="Restock",
                reason="Over-return",
            ).status_code,
            409,
        )
        r = self.client("pharmacist").get("/api/corrections/history")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            all(
                str(x["difference"]) in ("0", "0.0")
                for x in r.get_json()["data"]["reconciliation"]
            )
        )

    def bill(self):
        return self.saved(
            self.post(
                "cashier",
                "/api/bills",
                {
                    "patient_id": 1,
                    "bill_date": "2026-10-29",
                    "consultation_charge": "100.00",
                    "room_charge": "0",
                    "medicine_charge": "0",
                },
            )
        )

    def test_refund_retains_receipt_and_locks_historical_charges(self):
        bill = self.bill()
        payment = self.saved(
            self.post(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "100",
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        payload = dict(
            bill_id=bill,
            payment_id=payment,
            amount="25.00",
            reason="Authorized fee correction",
            idempotency_key=str(uuid.uuid4()),
        )
        r = self.op("manager", "refund", **payload)
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual(self.op("manager", "refund", **payload).status_code, 200)
        data = (
            self.client("patient").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertEqual(
            (data["billed"], data["paid"], data["balance"]), ("75.00", "75.00", "0.00")
        )
        self.assertEqual(len(data["payments"]), 1)
        self.assertEqual(len(data["corrections"]), 2)
        self.assertEqual(
            self.op(
                "manager",
                "refund",
                bill_id=bill,
                payment_id=payment,
                amount="76",
                reason="Over refund",
            ).status_code,
            409,
        )
        self.assertEqual(
            self.op(
                "cashier", "refund", **{**payload, "idempotency_key": str(uuid.uuid4())}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.op(
                "cashier", "credit", bill_id=bill, amount="1", reason="Not authorized"
            ).status_code,
            403,
        )

    def test_credit_writeoff_debit_and_void_have_explicit_history(self):
        bill = self.bill()
        for action, amount in [("credit", "10"), ("writeoff", "20"), ("debit", "5")]:
            self.assertEqual(
                self.op(
                    "manager",
                    action,
                    bill_id=bill,
                    amount=amount,
                    reason="Approved correction",
                ).status_code,
                201,
            )
        data = (
            self.client("cashier").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertEqual(data["balance"], "75.00")
        self.assertEqual(
            self.op(
                "manager",
                "void_invoice",
                bill_id=bill,
                reason="Duplicate unpaid administrative invoice",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client("cashier")
            .get(f"/api/bills/{bill}/ledger")
            .get_json()["data"]["status"],
            "Voided",
        )
        self.assertEqual(
            self.post(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "1",
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            ).status_code,
            409,
        )

    def test_profile_and_appointment_are_self_only(self):
        r = self.op("patient", "profile", phone="12345", address="Updated address")
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual(
            self.op("patient", "profile", patient_id=2, phone="Tamper").status_code, 400
        )

    def test_receive_batch_retry_cannot_duplicate_inventory(self):
        p = {
            "medicine_id": 1,
            "batch_number": "RETRY",
            "expires_on": "2099-01-01",
            "quantity": 5,
            "idempotency_key": str(uuid.uuid4()),
        }
        first = self.action("pharmacist", "receive_batch", p)
        self.assertEqual(first.status_code, 201)
        again = self.action("pharmacist", "receive_batch", p)
        self.assertEqual(again.status_code, 200, again.get_json())
        self.assertEqual(
            self.db.sql.execute(
                "SELECT stock_quantity FROM Medicine WHERE medicine_id=1"
            ).fetchone()[0],
            5,
        )

    def test_completed_result_amendment_is_released_but_other_orders_stay_scoped(self):
        eid = self.clinical()
        order = self.saved(
            self.action("doctor", "order_test", {"encounter_id": eid, "test_id": 1})
        )
        result = self.saved(
            self.action(
                "lab",
                "result",
                {"order_id": order, "result_text": "Original laboratory finding"},
            )
        )
        self.assertEqual(
            self.op(
                "lab",
                "amend_result",
                result_id=result,
                content="Corrected finding",
                reason="Verified instrument recalibration",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client("patient")
            .get("/api/corrections/history")
            .get_json()["data"]["amendments"],
            [],
        )
        self.assertEqual(
            self.client("patient")
            .get("/api/patients/1/summary")
            .get_json()["data"]["test_results"],
            [],
        )
        self.assertEqual(
            self.client("patient")
            .get("/api/workspace")
            .get_json()["data"]["queues"]["tests"],
            [],
        )
        self.saved(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": eid,
                    "diagnosis": "Reviewed",
                    "clinical_notes": "Released",
                },
            )
        )
        history = (
            self.client("patient").get("/api/patients/1/summary").get_json()["data"]
        )
        self.assertEqual(
            history["test_results"][0]["result_text"], "Original laboratory finding"
        )
        self.assertEqual(history["amendments"][0]["content"], "Corrected finding")
        self.assertTrue(
            any(
                "Corrected finding" in event["details"] for event in history["timeline"]
            )
        )
        self.assertEqual(
            self.op(
                "doctor",
                "cancel_test",
                order_id=order,
                reason="Cannot unperform a completed service",
            ).status_code,
            409,
        )
        self.assertEqual(
            self.op(
                "cashier",
                "amend_result",
                result_id=result,
                content="Denied",
                reason="Denied",
            ).status_code,
            403,
        )

    def test_partial_cancel_and_return_reduce_only_unbilled_actual_service(self):
        eid = self.clinical()
        rx = self.saved(
            self.action(
                "doctor",
                "prescribe",
                {
                    "encounter_id": eid,
                    "medicine_id": 1,
                    "ordered_quantity": 4,
                    "dosage": "One",
                    "duration": "Four days",
                },
            )
        )
        batch = self.saved(
            self.action(
                "pharmacist",
                "receive_batch",
                {
                    "medicine_id": 1,
                    "batch_number": "PART",
                    "expires_on": "2099-01-01",
                    "quantity": 10,
                },
            )
        )
        disp = self.saved(
            self.action(
                "pharmacist",
                "dispense",
                {
                    "prescription_id": rx,
                    "batch_id": batch,
                    "quantity": 2,
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        self.assertEqual(
            self.op(
                "doctor", "cancel_rx", prescription_id=rx, reason="Stop remaining units"
            ).status_code,
            201,
        )
        self.assertEqual(
            self.action(
                "pharmacist",
                "dispense",
                {
                    "prescription_id": rx,
                    "batch_id": batch,
                    "quantity": 1,
                    "idempotency_key": str(uuid.uuid4()),
                },
            ).status_code,
            409,
        )
        self.assertEqual(
            self.op(
                "pharmacist",
                "return_stock",
                dispense_id=disp,
                quantity=1,
                disposition="Quarantine",
                reason="Opened package cannot re-enter stock",
            ).status_code,
            201,
        )
        self.saved(
            self.action(
                "doctor",
                "complete_consultation",
                {"encounter_id": eid, "diagnosis": "Done", "clinical_notes": "Done"},
            )
        )
        bill = self.saved(self.action("cashier", "prepare_bill", {"encounter_id": eid}))
        d = self.client("cashier").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        self.assertEqual(d["billed"], "25.00")
        self.assertEqual(
            self.db.sql.execute(
                "SELECT quantity FROM HMS_Care_Charge WHERE source_kind='Dispense'"
            ).fetchone()[0],
            2,
        )
        self.assertEqual(
            self.db.sql.execute(
                "SELECT stock_quantity FROM Medicine WHERE medicine_id=1"
            ).fetchone()[0],
            8,
        )
        self.assertEqual(
            self.client("pharmacist")
            .get("/api/workspace")
            .get_json()["data"]["notifications"]["prescriptions"],
            0,
        )

    def test_financial_transaction_rolls_back_both_sides_on_audit_failure(self):
        from unittest.mock import patch

        bill = self.bill()
        pay = self.saved(
            self.post(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "100",
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        with patch(
            "hms.corrections.audit", side_effect=RuntimeError("Injected rollback")
        ):
            with self.assertLogs(self.app.logger, level="ERROR"):
                self.assertEqual(
                    self.op(
                        "manager",
                        "refund",
                        bill_id=bill,
                        payment_id=pay,
                        amount="10",
                        reason="Atomic rollback test",
                    ).status_code,
                    500,
                )
        self.assertEqual(
            self.db.sql.execute("SELECT COUNT(*) FROM HMS_Fin_Event").fetchone()[0], 0
        )
        self.assertEqual(
            self.db.sql.execute("SELECT COUNT(*) FROM HMS_Operation").fetchone()[0], 0
        )
        self.assertEqual(
            self.db.sql.execute("SELECT amount FROM Bill_Payment").fetchone()[0], 100
        )

    def test_full_refund_never_reopens_item_or_base_mutations(self):
        bill = self.bill()
        pay = self.saved(
            self.post(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "100",
                    "payment_method": "Card",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        r = self.post(
            "manager",
            f"/api/bills/{bill}/refunds",
            {
                "payment_id": pay,
                "amount": "100",
                "reason": "Entire charge returned",
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual(
            self.post(
                "cashier",
                f"/api/bills/{bill}/items",
                {"description": "Must not reopen", "quantity": 1, "unit_price": "1"},
            ).status_code,
            409,
        )
        r = self.client("manager").put(
            f"/api/bills/{bill}",
            json={"consultation_charge": "101"},
            headers={"X-CSRF-Token": self.csrf["manager"]},
        )
        self.assertEqual(r.status_code, 409, r.get_json())
        ledger = (
            self.client("patient").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertTrue(ledger["charges_locked"])
        self.assertEqual(
            (ledger["gross_paid"], ledger["refunds"], ledger["paid"]),
            ("100.00", "100.00", "0.00"),
        )

    def test_patient_reschedule_overlap_cancel_and_record_id_tampering(self):
        from hms.api import hospital_today

        day = hospital_today().isoformat()
        appt = self.saved(
            self.post(
                "receptionist",
                "/api/appointments",
                {
                    "patient_id": 1,
                    "doctor_id": 1,
                    "appointment_date": day,
                    "appointment_time": "13:00",
                },
            )
        )
        other = self.saved(
            self.post(
                "receptionist",
                "/api/appointments",
                {
                    "patient_id": 2,
                    "doctor_id": 1,
                    "appointment_date": day,
                    "appointment_time": "14:00",
                },
            )
        )
        self.assertEqual(
            self.op(
                "patient",
                "reschedule_appointment",
                appointment_id=appt,
                appointment_date=day,
                appointment_time="14:00",
                reason="Conflicts with another appointment",
            ).status_code,
            409,
        )
        self.assertEqual(
            self.op(
                "patient",
                "reschedule_appointment",
                appointment_id=appt,
                appointment_date=day,
                appointment_time="15:00",
                reason="Requested different time",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.op(
                "patient",
                "cancel_appointment",
                appointment_id=other,
                reason="Tampered ID",
            ).status_code,
            404,
        )
        self.assertEqual(
            self.op(
                "patient",
                "cancel_appointment",
                appointment_id=appt,
                reason="No longer needed",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.op(
                "patient",
                "reschedule_appointment",
                appointment_id=appt,
                appointment_date=day,
                appointment_time="16:00",
                reason="Cannot reopen",
            ).status_code,
            409,
        )

    def test_correction_idempotency_mismatch_revocation_and_csrf(self):
        bill = self.bill()
        key = str(uuid.uuid4())
        p = dict(bill_id=bill, amount="1", reason="Approved", idempotency_key=key)
        self.assertEqual(self.op("manager", "credit", **p).status_code, 201)
        self.assertEqual(
            self.op("manager", "credit", **{**p, "amount": "2"}).status_code, 409
        )
        self.assertEqual(self.op("manager", "debit", **p).status_code, 409)
        self.assertEqual(
            self.client("manager")
            .post(
                "/api/corrections/credit",
                json={**p, "idempotency_key": str(uuid.uuid4())},
            )
            .status_code,
            403,
        )
        self.db.sql.execute("UPDATE HMS_User SET is_active='N' WHERE role='manager'")
        self.db.sql.commit()
        self.assertEqual(self.op("manager", "credit", **p).status_code, 401)
        self.assertEqual(
            self.client("maintenance").get("/api/corrections/history").status_code, 403
        )

    def test_expired_return_quarantine_and_writeoff_preserve_reconciliation(self):
        eid = self.clinical()
        rx = self.saved(
            self.action(
                "doctor",
                "prescribe",
                {
                    "encounter_id": eid,
                    "medicine_id": 1,
                    "ordered_quantity": 1,
                    "dosage": "One",
                    "duration": "One day",
                },
            )
        )
        batch = self.saved(
            self.action(
                "pharmacist",
                "receive_batch",
                {
                    "medicine_id": 1,
                    "batch_number": "EXP",
                    "expires_on": "2099-01-01",
                    "quantity": 5,
                },
            )
        )
        disp = self.saved(
            self.action(
                "pharmacist",
                "dispense",
                {
                    "prescription_id": rx,
                    "batch_id": batch,
                    "quantity": 1,
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        self.db.sql.execute("UPDATE HMS_Medicine_Batch SET expires_on='2000-01-01'")
        self.db.sql.commit()
        self.assertEqual(
            self.op(
                "pharmacist",
                "return_stock",
                dispense_id=disp,
                quantity=1,
                disposition="Restock",
                reason="Expired now",
            ).status_code,
            409,
        )
        self.assertEqual(
            self.op(
                "pharmacist",
                "return_stock",
                dispense_id=disp,
                quantity=1,
                disposition="Quarantine",
                reason="Expired patient return",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.op(
                "pharmacist",
                "write_off",
                batch_id=batch,
                quantity=4,
                reason="Expired remaining units",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.op(
                "manager",
                "adjust_add",
                batch_id=batch,
                quantity=1,
                reason="Expired additions prohibited",
            ).status_code,
            409,
        )
        self.assertEqual(
            self.db.sql.execute("SELECT difference FROM V_HMS_Batch_Recon").fetchone()[
                0
            ],
            0,
        )
        self.assertEqual(
            self.db.sql.execute(
                "SELECT stock_quantity FROM Medicine WHERE medicine_id=1"
            ).fetchone()[0],
            0,
        )

    def test_financial_reports_exports_and_dashboard_reconcile_net_cash(self):
        bill = self.bill()
        pay = self.saved(
            self.post(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "60",
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        self.assertEqual(
            self.op(
                "manager",
                "refund",
                bill_id=bill,
                payment_id=pay,
                amount="10",
                reason="Reduce agreed charge and return cash",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.op(
                "manager",
                "writeoff",
                bill_id=bill,
                amount="5",
                reason="Authorized remaining debt waiver",
            ).status_code,
            201,
        )
        ledger = (
            self.client("manager").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertEqual(
            (ledger["billed"], ledger["paid"], ledger["balance"]),
            ("85.00", "50.00", "35.00"),
        )
        dash = self.client("manager").get("/api/dashboard")
        self.assertEqual(dash.status_code, 200, dash.get_json())
        self.assertEqual(
            (
                dash.get_json()["data"]["collected_total"],
                dash.get_json()["data"]["outstanding_total"],
            ),
            ("50.00", "35.00"),
        )
        for name in [
            "patient-bills",
            "invoice-balances",
            "billing-by-status",
            "monthly-revenue",
        ]:
            r = self.client("manager").get("/api/reports/" + name)
            self.assertEqual(r.status_code, 200, r.get_json())
            export = self.client("manager").get("/api/reports/" + name + "/csv")
            self.assertEqual(export.status_code, 200, export.get_data(as_text=True))
            self.assertIn("50", export.get_data(as_text=True))
        month = (
            self.client("manager")
            .get("/api/reports/monthly-revenue")
            .get_json()["data"]
        )
        self.assertEqual(sum(float(r["collected_total"]) for r in month), 50)
        self.assertEqual(sum(float(r["outstanding_total"]) for r in month), 35)
        self.assertEqual(
            self.client("patient").get("/api/reports/monthly-revenue/csv").status_code,
            403,
        )

    def test_billed_medicine_return_links_credit_at_original_price_and_only_once(self):
        eid = self.clinical()
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
        batch = self.saved(
            self.action(
                "pharmacist",
                "receive_batch",
                {
                    "medicine_id": 1,
                    "batch_number": "BILLED",
                    "expires_on": "2099-01-01",
                    "quantity": 5,
                },
            )
        )
        disp = self.saved(
            self.action(
                "pharmacist",
                "dispense",
                {
                    "prescription_id": rx,
                    "batch_id": batch,
                    "quantity": 2,
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        self.saved(
            self.action(
                "doctor",
                "complete_consultation",
                {"encounter_id": eid, "diagnosis": "Done", "clinical_notes": "Done"},
            )
        )
        bill = self.saved(self.action("cashier", "prepare_bill", {"encounter_id": eid}))
        pay = self.saved(
            self.post(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "30",
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        returned = self.saved(
            self.op(
                "pharmacist",
                "return_stock",
                dispense_id=disp,
                quantity=1,
                disposition="Restock",
                reason="Verified unopened return",
            )
        )
        self.db.sql.execute("UPDATE Medicine SET price=999 WHERE medicine_id=1")
        self.db.sql.commit()
        review = (
            self.client("cashier")
            .get("/api/workspace")
            .get_json()["data"]["queues"]["return_review"]
        )
        self.assertEqual(review[0]["remaining_credit"], "5.00")
        self.assertEqual(
            self.op(
                "manager",
                "refund",
                bill_id=bill,
                payment_id=pay,
                stock_event_id=returned,
                amount="6",
                reason="Above original price",
            ).status_code,
            409,
        )
        self.assertEqual(
            self.op(
                "cashier",
                "refund",
                bill_id=bill,
                payment_id=pay,
                stock_event_id=returned,
                amount="5",
                reason="Authorized original-price goods return",
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client("cashier")
            .get("/api/workspace")
            .get_json()["data"]["queues"]["return_review"],
            [],
        )
        self.assertEqual(
            self.op(
                "manager",
                "refund",
                bill_id=bill,
                payment_id=pay,
                stock_event_id=returned,
                amount="1",
                reason="Duplicate return credit",
            ).status_code,
            409,
        )
        ledger = (
            self.client("patient").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertEqual(ledger["billed"], "25.00")
        self.assertEqual(
            ledger["corrections"][1]["related_event_id"],
            ledger["corrections"][0]["event_id"],
        )

    def test_two_concurrent_refunds_cannot_overrefund_one_receipt(self):
        from concurrent.futures import ThreadPoolExecutor

        bill = self.bill()
        pay = self.saved(
            self.post(
                "cashier",
                f"/api/bills/{bill}/payments",
                {
                    "amount": "100",
                    "payment_method": "Cash",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        )
        requests = []
        for _ in range(2):
            client = self.app.test_client()
            token = client.post(
                "/api/auth/login",
                json={"username": "manager", "password": "fixture-password-only"},
            ).get_json()["data"]["csrf_token"]
            requests.append((client, token))

        def refund(pair):
            client, token = pair
            return client.post(
                "/api/corrections/refund",
                json={
                    "bill_id": bill,
                    "payment_id": pay,
                    "amount": "75",
                    "reason": "Competing authorized refund",
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"X-CSRF-Token": token},
            ).status_code

        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(refund, requests)), [201, 409])
        ledger = (
            self.client("patient").get(f"/api/bills/{bill}/ledger").get_json()["data"]
        )
        self.assertEqual(ledger["paid"], "25.00")
        self.assertEqual(len(ledger["corrections"]), 2)

    def test_role_history_is_bounded_and_clinical_events_never_leak_to_cashier(self):
        eid = self.clinical()
        self.saved(
            self.action(
                "doctor",
                "complete_consultation",
                {
                    "encounter_id": eid,
                    "diagnosis": "Done",
                    "clinical_notes": "Retained original",
                },
            )
        )
        for n in range(43):
            self.assertEqual(
                self.op(
                    "doctor",
                    "amend_consultation",
                    encounter_id=eid,
                    content="Clinical detail " + str(n),
                    reason="Verified historical clarification",
                ).status_code,
                201,
            )
        first = (
            self.client("patient")
            .get("/api/corrections/history?page=1")
            .get_json()["data"]
        )
        second = (
            self.client("patient")
            .get("/api/corrections/history?page=2")
            .get_json()["data"]
        )
        self.assertEqual(
            (
                len(first["amendments"]),
                len(second["amendments"]),
                first["counts"]["amendments"],
            ),
            (40, 3, 43),
        )
        self.assertNotIn(
            "amendments",
            self.client("cashier").get("/api/corrections/history").get_json()["data"],
        )
        self.assertNotIn(
            "Retained original",
            self.client("pharmacist")
            .get("/api/corrections/history")
            .get_data(as_text=True),
        )

    def test_receipt_requires_a_durable_key_and_allows_distinct_consignments_of_same_batch(
        self,
    ):
        payload = {
            "medicine_id": 1,
            "batch_number": "SAME",
            "expires_on": "2099-01-01",
            "quantity": 3,
        }
        self.assertEqual(
            self.post("pharmacist", "/api/work/receive_batch", payload).status_code, 400
        )
        first = self.saved(
            self.action(
                "pharmacist",
                "receive_batch",
                {**payload, "idempotency_key": str(uuid.uuid4())},
            )
        )
        second = self.saved(
            self.action(
                "pharmacist",
                "receive_batch",
                {**payload, "quantity": 2, "idempotency_key": str(uuid.uuid4())},
            )
        )
        self.assertEqual(first, second)
        self.assertEqual(
            self.db.sql.execute(
                "SELECT stock_quantity FROM Medicine WHERE medicine_id=1"
            ).fetchone()[0],
            5,
        )
        self.assertEqual(
            self.db.sql.execute("SELECT COUNT(*) FROM HMS_Stock_Event").fetchone()[0], 2
        )
        self.assertEqual(
            self.action(
                "pharmacist",
                "receive_batch",
                {
                    **payload,
                    "expires_on": "2098-01-01",
                    "idempotency_key": str(uuid.uuid4()),
                },
            ).status_code,
            409,
        )

    def test_today_queue_matches_same_day_upcoming_appointment(self):
        from hms.api import hospital_today

        self.saved(
            self.post(
                "receptionist",
                "/api/appointments",
                {
                    "patient_id": 1,
                    "doctor_id": 1,
                    "appointment_date": hospital_today().isoformat(),
                    "appointment_time": "19:00",
                },
            )
        )
        data = self.client("manager").get("/api/dashboard").get_json()["data"]
        self.assertEqual(data["counts"]["today_queue_appointments"], 1)
        self.assertEqual(len(data["upcoming_appointments"]), 1)

    def test_successful_personal_logins_do_not_exhaust_failed_attempt_budget(self):
        client = self.app.test_client()
        for attempt in range(10):
            response = client.post(
                "/api/auth/login",
                json={"username": "manager", "password": "fixture-password-only"},
            )
            self.assertEqual(response.status_code, 200, (attempt, response.get_json()))
        for _ in range(8):
            self.assertEqual(
                client.post(
                    "/api/auth/login",
                    json={"username": "manager", "password": "incorrect-password"},
                ).status_code,
                401,
            )
        self.assertEqual(
            client.post(
                "/api/auth/login",
                json={"username": "manager", "password": "fixture-password-only"},
            ).status_code,
            429,
        )


class CorrectionSqlContractTests(unittest.TestCase):
    def test_additive_schema_inventory_and_fail_stop_marker(self):
        import pathlib
        import re

        migration = pathlib.Path("sql/migrations/008_corrections.sql").read_text()
        self.assertEqual(len(re.findall(r"CREATE TABLE ", migration)), 7)
        self.assertEqual(len(re.findall(r"GENERATED ALWAYS AS IDENTITY", migration)), 4)
        self.assertEqual(len(re.findall(r"REFERENCES ", migration)), 18)
        self.assertLess(
            migration.index("@@../12_correction_invariants.sql"),
            migration.index("SET correction_version=1"),
        )
        self.assertIn("Do not rerun", migration)
        for path in re.findall(r"@@(\S+)", migration):
            self.assertTrue((pathlib.Path("sql/migrations") / path).resolve().is_file())

    def test_financial_pair_checks_are_not_in_mutating_row_trigger(self):
        from pathlib import Path

        sql = (
            Path("sql/migrations/008_corrections.sql")
            .read_text()
            .split("TRIGGER trg_cc_fin", 1)[1]
        )
        row_part = sql.split("END BEFORE EACH ROW;", 1)[0]
        self.assertNotIn("FROM HMS_Fin_Event", row_part)
        self.assertNotIn("FROM V_HMS_Return_Review", row_part)
        self.assertIn("AFTER STATEMENT", sql)
        self.assertIn("related_event_id", sql)

    def test_runtime_grants_cannot_rewrite_corrective_or_cutover_facts(self):
        from pathlib import Path

        sql = Path("sql/10_corrections_grants.sql").read_text()
        self.assertNotIn("GRANT UPDATE", sql)
        self.assertNotIn("GRANT DELETE", sql)
        self.assertNotIn("GRANT ALL", sql)
        self.assertIn("GRANT SELECT,INSERT", sql)
        self.assertIn("HMS_Stock_Opening", sql)

    def test_007_postflight_counts_distinct_trigger_objects_not_replacements(self):
        import re
        from pathlib import Path

        migration = Path("sql/migrations/007_multiuser.sql").read_text()
        verification = Path("sql/09_multiuser_verification.sql").read_text()
        installed = set(re.findall(r"CREATE OR REPLACE TRIGGER (\w+)", migration, re.I))
        inventory = verification.split("trigger_name IN (", 1)[1].split(");", 1)[0]
        names = re.findall(r"'(TRG_\w+)'", inventory)
        self.assertEqual(
            len(names),
            len(set(names)),
            "Oracle replaces duplicate trigger names; it does not create another object",
        )
        self.assertEqual({name.lower() for name in names}, installed)
        expected = re.search(
            r"IF n<>(\d+) THEN RAISE_APPLICATION_ERROR\(-20200,'Missing/disabled expected007 trigger",
            verification,
        )
        self.assertIsNotNone(expected)
        self.assertEqual(int(expected.group(1)), len(names))
        base = (
            Path("sql/01_create_schema.sql").read_text()
            + Path("sql/05_integrity_objects.sql").read_text()
        )
        baseline = set(re.findall(r"CREATE OR REPLACE TRIGGER (\w+)", base, re.I))
        baseline.difference_update(re.findall(r"DROP TRIGGER (\w+)", base, re.I))
        self.assertEqual(len(baseline), 35)
        self.assertEqual(len(baseline | installed), 70)
