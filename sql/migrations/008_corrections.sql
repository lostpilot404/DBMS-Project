-- Additive corrective-event extension AFTER007, owner only, Oracle12c+.
-- STOP ALL writers, back up and rehearse a disposable clone. DDL implicitly commits.
-- Any error: leave application stopped; inspect partial objects; restore reviewed backup.
-- NEVER rerun a partially applied migration. Historical receipts/notes are NOT rewritten.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM HMS_Settings WHERE schema_version=6 AND multiuser_version=1;
 IF n<>1 THEN RAISE_APPLICATION_ERROR(-20210,'Complete007 first.'); END IF;
 SELECT COUNT(*) INTO n FROM user_objects WHERE status='INVALID';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20210,'Repair invalid baseline objects.'); END IF;
 SELECT COUNT(*) INTO n FROM user_tab_cols WHERE table_name='HMS_SETTINGS' AND column_name='CORRECTION_VERSION';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20210,'008 already/partly applied. Do not rerun.'); END IF;
 SELECT COUNT(*) INTO n FROM Medicine m WHERE stock_quantity<NVL((SELECT SUM(quantity) FROM HMS_Medicine_Batch b WHERE b.medicine_id=m.medicine_id),0);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20210,'Batch totals exceed stock. Investigate first.'); END IF;
END;
/
@@../09_multiuser_verification.sql
ALTER TABLE HMS_Settings ADD(correction_version NUMBER(2) DEFAULT 0 NOT NULL,stock_cutover_id NUMBER(10) DEFAULT 0 NOT NULL);
CREATE TABLE HMS_Operation(operation_key VARCHAR2(36) PRIMARY KEY,user_id NUMBER(10) NOT NULL REFERENCES HMS_User,action VARCHAR2(40) NOT NULL,payload_hash VARCHAR2(64) NOT NULL,result_id NUMBER(10) NOT NULL,reason VARCHAR2(500) NOT NULL,recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL);
CREATE TABLE HMS_Amendment(amendment_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,encounter_id NUMBER(10) REFERENCES HMS_Encounter,result_id NUMBER(10) REFERENCES HMS_Test_Result,content VARCHAR2(2000) NOT NULL,reason VARCHAR2(500) NOT NULL,user_id NUMBER(10) NOT NULL REFERENCES HMS_User,recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL,CHECK((encounter_id IS NOT NULL AND result_id IS NULL) OR (encounter_id IS NULL AND result_id IS NOT NULL)));
CREATE TABLE HMS_Order_Cancel(cancellation_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,prescription_id NUMBER(10) UNIQUE REFERENCES Prescription,order_id NUMBER(10) UNIQUE REFERENCES HMS_Test_Order,reason VARCHAR2(500) NOT NULL,user_id NUMBER(10) NOT NULL REFERENCES HMS_User,recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL,CHECK((prescription_id IS NOT NULL AND order_id IS NULL) OR (prescription_id IS NULL AND order_id IS NOT NULL)));
CREATE TABLE HMS_Stock_Opening(batch_id NUMBER(10) PRIMARY KEY REFERENCES HMS_Medicine_Batch,quantity NUMBER(10) NOT NULL CHECK(quantity>=0),recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL);
CREATE TABLE HMS_Legacy_Stock(medicine_id NUMBER(10) PRIMARY KEY REFERENCES Medicine,quantity NUMBER(10) NOT NULL CHECK(quantity>=0),recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL);
CREATE TABLE HMS_Stock_Event(event_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,event_kind VARCHAR2(25) NOT NULL CHECK(event_kind IN ('RECEIPT','RETURN_RESTOCK','RETURN_QUARANTINE','WRITE_OFF','ADJUST_ADD','ADJUST_REMOVE')),medicine_id NUMBER(10) NOT NULL REFERENCES Medicine,batch_id NUMBER(10) NOT NULL REFERENCES HMS_Medicine_Batch,dispense_id NUMBER(10) REFERENCES HMS_Dispense,quantity NUMBER(10) NOT NULL CHECK(quantity>0),user_id NUMBER(10) NOT NULL REFERENCES HMS_User,reason VARCHAR2(500) NOT NULL,recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL,CHECK((event_kind IN ('RETURN_RESTOCK','RETURN_QUARANTINE') AND dispense_id IS NOT NULL) OR (event_kind NOT IN ('RETURN_RESTOCK','RETURN_QUARANTINE') AND dispense_id IS NULL)));
CREATE TABLE HMS_Fin_Event(event_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,bill_id NUMBER(10) NOT NULL REFERENCES Bill,event_kind VARCHAR2(20) NOT NULL CHECK(event_kind IN ('CREDIT','DEBIT','WRITE_OFF','REFUND','REFUND_CREDIT','VOID')),amount NUMBER(10,2) NOT NULL CHECK(amount>0),payment_id NUMBER(10) REFERENCES Bill_Payment,related_event_id NUMBER(10) REFERENCES HMS_Fin_Event,stock_event_id NUMBER(10) REFERENCES HMS_Stock_Event,user_id NUMBER(10) NOT NULL REFERENCES HMS_User,reason VARCHAR2(500) NOT NULL,recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL,CHECK((event_kind='REFUND' AND payment_id IS NOT NULL) OR (event_kind<>'REFUND' AND payment_id IS NULL)),CHECK((event_kind='REFUND_CREDIT' AND related_event_id IS NOT NULL) OR (event_kind<>'REFUND_CREDIT' AND related_event_id IS NULL)));
-- Observed available quantities only. These are NOT reconstructed old receipts.
INSERT INTO HMS_Stock_Opening(batch_id,quantity) SELECT batch_id,quantity FROM HMS_Medicine_Batch;
INSERT INTO HMS_Legacy_Stock(medicine_id,quantity)
 SELECT m.medicine_id,m.stock_quantity-NVL((SELECT SUM(quantity) FROM HMS_Medicine_Batch b WHERE b.medicine_id=m.medicine_id),0) FROM Medicine m;
UPDATE HMS_Settings SET stock_cutover_id=(SELECT NVL(MAX(dispense_id),0) FROM HMS_Dispense) WHERE singleton=1;
CREATE OR REPLACE VIEW V_Invoice_Balances AS
SELECT x.*,x.gross_billed+x.debits-x.credits-x.written_off billed,x.gross_paid-x.refunds paid,
 x.gross_billed+x.debits-x.credits-x.written_off-x.gross_paid+x.refunds balance,
 CASE WHEN x.void_count>0 THEN 'Voided'
 WHEN x.gross_billed+x.debits-x.credits-x.written_off=x.gross_paid-x.refunds THEN 'Paid'
 WHEN x.gross_paid=x.refunds THEN 'Unpaid' ELSE 'Partial' END ledger_status
FROM (SELECT b.bill_id,b.patient_id,b.bill_date,b.notes,b.consultation_charge,b.room_charge,b.medicine_charge,
 b.payment_status legacy_status,b.total_amount legacy_charges,NVL(i.item_total,0) item_total,
 b.total_amount+NVL(i.item_total,0) gross_billed,NVL(p.paid_total,0) gross_paid,
 NVL(f.debits,0) debits,NVL(f.credits,0) credits,NVL(f.written_off,0) written_off,NVL(f.refunds,0) refunds,
 NVL(f.void_count,0) void_count,NVL(f.correction_count,0) correction_count
 FROM Bill b LEFT JOIN(SELECT bill_id,SUM(line_total) item_total FROM Bill_Item GROUP BY bill_id)i ON i.bill_id=b.bill_id
 LEFT JOIN(SELECT bill_id,SUM(amount) paid_total FROM Bill_Payment GROUP BY bill_id)p ON p.bill_id=b.bill_id
 LEFT JOIN(SELECT bill_id,SUM(CASE WHEN event_kind='DEBIT' THEN amount ELSE 0 END) debits,
 SUM(CASE WHEN event_kind IN ('CREDIT','REFUND_CREDIT','VOID') THEN amount ELSE 0 END) credits,
 SUM(CASE WHEN event_kind='WRITE_OFF' THEN amount ELSE 0 END) written_off,
 SUM(CASE WHEN event_kind='REFUND' THEN amount ELSE 0 END) refunds,
 SUM(CASE WHEN event_kind='VOID' THEN 1 ELSE 0 END) void_count,COUNT(*) correction_count
 FROM HMS_Fin_Event GROUP BY bill_id)f ON f.bill_id=b.bill_id)x;
CREATE OR REPLACE VIEW V_HMS_Cash_Events AS
 SELECT bill_id,amount,recorded_at,recorded_timezone FROM Bill_Payment
 UNION ALL SELECT bill_id,-amount,recorded_at,'UTC' FROM HMS_Fin_Event WHERE event_kind='REFUND';
CREATE OR REPLACE VIEW V_HMS_Batch_Recon AS
SELECT b.batch_id,b.medicine_id,b.quantity,
 NVL(o.quantity,0)+NVL(s.net_quantity,0)-NVL(d.dispensed,0) expected_quantity,
 b.quantity-NVL(o.quantity,0)-NVL(s.net_quantity,0)+NVL(d.dispensed,0) difference
FROM HMS_Medicine_Batch b LEFT JOIN HMS_Stock_Opening o ON o.batch_id=b.batch_id
LEFT JOIN(SELECT batch_id,SUM(CASE WHEN event_kind IN ('RECEIPT','RETURN_RESTOCK','ADJUST_ADD') THEN quantity
 WHEN event_kind IN ('WRITE_OFF','ADJUST_REMOVE') THEN -quantity ELSE 0 END) net_quantity
 FROM HMS_Stock_Event GROUP BY batch_id)s ON s.batch_id=b.batch_id
LEFT JOIN(SELECT batch_id,SUM(quantity) dispensed FROM HMS_Dispense CROSS JOIN HMS_Settings
 WHERE dispense_id>stock_cutover_id GROUP BY batch_id)d ON d.batch_id=b.batch_id;
CREATE OR REPLACE VIEW V_HMS_Medicine_Recon AS
SELECT m.medicine_id,m.stock_quantity,NVL(l.quantity,0) legacy_quantity,
 NVL(l.quantity,0)+NVL(b.quantity,0) expected_quantity,
 m.stock_quantity-NVL(l.quantity,0)-NVL(b.quantity,0) difference
FROM Medicine m LEFT JOIN HMS_Legacy_Stock l ON l.medicine_id=m.medicine_id
LEFT JOIN(SELECT medicine_id,SUM(quantity) quantity FROM HMS_Medicine_Batch GROUP BY medicine_id)b ON b.medicine_id=m.medicine_id;
CREATE OR REPLACE VIEW V_HMS_Care_Net AS
SELECT c.charge_id,c.encounter_id,c.source_kind,c.source_id,c.description,c.unit_price,c.bill_item_id,
 c.quantity-NVL(r.returned_quantity,0) quantity
FROM HMS_Care_Charge c LEFT JOIN(SELECT dispense_id,SUM(quantity) returned_quantity
 FROM HMS_Stock_Event WHERE event_kind IN ('RETURN_RESTOCK','RETURN_QUARANTINE') GROUP BY dispense_id)r
 ON c.source_kind='Dispense' AND r.dispense_id=c.source_id
WHERE NOT EXISTS(SELECT 1 FROM HMS_Order_Cancel x WHERE c.source_kind='Test' AND x.order_id=c.source_id);
CREATE OR REPLACE VIEW V_HMS_Return_Review AS
SELECT s.event_id,i.bill_id,b.patient_id,s.dispense_id,s.quantity,c.unit_price,
 s.quantity*c.unit_price eligible_credit,NVL(f.credited,0) credited,
 s.quantity*c.unit_price-NVL(f.credited,0) remaining_credit
FROM HMS_Stock_Event s JOIN HMS_Care_Charge c ON c.source_kind='Dispense' AND c.source_id=s.dispense_id
JOIN Bill_Item i ON i.item_id=c.bill_item_id JOIN Bill b ON b.bill_id=i.bill_id
LEFT JOIN(SELECT stock_event_id,SUM(amount) credited FROM HMS_Fin_Event
 WHERE event_kind IN ('CREDIT','REFUND_CREDIT','WRITE_OFF') GROUP BY stock_event_id)f ON f.stock_event_id=s.event_id
WHERE s.event_kind IN ('RETURN_RESTOCK','RETURN_QUARANTINE');
-- Every new foreign key has a leading index (PK/UNIQUE covers the others).
CREATE INDEX ix_cc_op_user ON HMS_Operation(user_id);
CREATE INDEX ix_cc_amend_enc ON HMS_Amendment(encounter_id);
CREATE INDEX ix_cc_amend_result ON HMS_Amendment(result_id);
CREATE INDEX ix_cc_amend_user ON HMS_Amendment(user_id);
CREATE INDEX ix_cc_cancel_user ON HMS_Order_Cancel(user_id);
CREATE INDEX ix_cc_stock_med ON HMS_Stock_Event(medicine_id);
CREATE INDEX ix_cc_stock_batch ON HMS_Stock_Event(batch_id);
CREATE INDEX ix_cc_stock_disp ON HMS_Stock_Event(dispense_id);
CREATE INDEX ix_cc_stock_user ON HMS_Stock_Event(user_id);
CREATE INDEX ix_cc_fin_bill ON HMS_Fin_Event(bill_id);
CREATE INDEX ix_cc_fin_pay ON HMS_Fin_Event(payment_id);
CREATE INDEX ix_cc_fin_user ON HMS_Fin_Event(user_id);
CREATE INDEX ix_cc_fin_related ON HMS_Fin_Event(related_event_id);
CREATE INDEX ix_cc_fin_stock ON HMS_Fin_Event(stock_event_id);
CREATE UNIQUE INDEX uq_cc_void ON HMS_Fin_Event(CASE WHEN event_kind='VOID' THEN bill_id END);
CREATE UNIQUE INDEX uq_cc_refund_credit ON HMS_Fin_Event(related_event_id);

-- Reuse the v6 mutex-first protocol. All new facts/snapshots are append-only.
BEGIN
 FOR t IN (SELECT column_value n FROM TABLE(SYS.ODCIVARCHAR2LIST(
 'operation','amendment','order_cancel','stock_opening','legacy_stock','stock_event','fin_event'))) LOOP
  EXECUTE IMMEDIATE 'CREATE OR REPLACE TRIGGER trg_cc_lock_'||t.n||' BEFORE INSERT OR UPDATE OR DELETE ON HMS_'||t.n||' DECLARE n NUMBER; BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;';
  EXECUTE IMMEDIATE 'CREATE OR REPLACE TRIGGER trg_cc_keep_'||t.n||' BEFORE UPDATE OR DELETE ON HMS_'||t.n||' FOR EACH ROW BEGIN RAISE_APPLICATION_ERROR(-20211,''Corrective event and observed cutover history is retained.''); END;';
 END LOOP;
END;
/
CREATE OR REPLACE TRIGGER trg_cc_amend BEFORE INSERT ON HMS_Amendment FOR EACH ROW
DECLARE r VARCHAR2(20); d NUMBER; owner_id NUMBER; s VARCHAR2(20);
BEGIN
 SELECT role,doctor_id INTO r,d FROM HMS_User WHERE user_id=:NEW.user_id AND is_active='Y';
 IF :NEW.encounter_id IS NOT NULL THEN
  SELECT doctor_id,status INTO owner_id,s FROM HMS_Encounter WHERE encounter_id=:NEW.encounter_id;
  IF s<>'Completed' OR (r<>'manager' AND (r<>'doctor' OR d<>owner_id)) THEN
   RAISE_APPLICATION_ERROR(-20211,'Only treating doctor/manager may amend completed consultation.'); END IF;
 ELSE
  IF r NOT IN ('lab','manager') THEN RAISE_APPLICATION_ERROR(-20211,'Only lab/manager may amend results.'); END IF;
 END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_cc_cancel BEFORE INSERT ON HMS_Order_Cancel FOR EACH ROW
DECLARE eid NUMBER; owner_id NUMBER; r VARCHAR2(20); d NUMBER; s VARCHAR2(20); n NUMBER; remaining NUMBER;
BEGIN
 SELECT role,doctor_id INTO r,d FROM HMS_User WHERE user_id=:NEW.user_id AND is_active='Y';
 IF :NEW.prescription_id IS NOT NULL THEN
  SELECT encounter_id,ordered_quantity INTO eid,remaining FROM Prescription WHERE prescription_id=:NEW.prescription_id;
  SELECT NVL(SUM(quantity),0) INTO n FROM HMS_Dispense WHERE prescription_id=:NEW.prescription_id;
  IF eid IS NULL OR remaining<=n THEN RAISE_APPLICATION_ERROR(-20211,'No linked remaining prescription.'); END IF;
 ELSE
  SELECT encounter_id,status INTO eid,s FROM HMS_Test_Order WHERE order_id=:NEW.order_id;
  SELECT COUNT(*) INTO n FROM HMS_Care_Charge WHERE source_kind='Test' AND source_id=:NEW.order_id AND bill_item_id IS NOT NULL;
  IF s<>'Ordered' OR n>0 THEN RAISE_APPLICATION_ERROR(-20211,'Performed/billed test cannot be cancelled.'); END IF;
 END IF;
 SELECT doctor_id INTO owner_id FROM HMS_Encounter WHERE encounter_id=eid;
 IF r<>'manager' AND (r<>'doctor' OR d<>owner_id) THEN RAISE_APPLICATION_ERROR(-20211,'Only treating doctor/manager may cancel remaining orders.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_cc_result BEFORE INSERT ON HMS_Test_Result FOR EACH ROW
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM HMS_Order_Cancel WHERE order_id=:NEW.order_id;
 IF n>0 THEN RAISE_APPLICATION_ERROR(-20211,'Cancelled test cannot receive a result.'); END IF;
END;
/
-- Multi-row safety: sums are checked AFTER STATEMENT, never on a mutating table.
CREATE OR REPLACE TRIGGER trg_cc_dispense FOR INSERT ON HMS_Dispense COMPOUND TRIGGER
 AFTER STATEMENT IS n NUMBER;
 BEGIN
  SELECT COUNT(*) INTO n FROM Prescription rx WHERE rx.encounter_id IS NOT NULL AND
   NVL((SELECT SUM(d.quantity) FROM HMS_Dispense d WHERE d.prescription_id=rx.prescription_id),0)>rx.ordered_quantity;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20212,'Dispensing exceeds ordered quantity.'); END IF;
 END AFTER STATEMENT;
 BEFORE EACH ROW IS n NUMBER; mid NUMBER; bid_mid NUMBER;
 BEGIN
  SELECT COUNT(*) INTO n FROM HMS_Order_Cancel WHERE prescription_id=:NEW.prescription_id;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20211,'Cancelled prescription cannot be dispensed.'); END IF;
  SELECT medicine_id INTO mid FROM Prescription WHERE prescription_id=:NEW.prescription_id;
  SELECT medicine_id INTO bid_mid FROM HMS_Medicine_Batch WHERE batch_id=:NEW.batch_id;
  IF mid<>bid_mid THEN RAISE_APPLICATION_ERROR(-20212,'Dispense batch medicine mismatch.'); END IF;
 END BEFORE EACH ROW;
END;
/
CREATE OR REPLACE TRIGGER trg_cc_stock FOR INSERT ON HMS_Stock_Event COMPOUND TRIGGER
 BEFORE EACH ROW IS mid NUMBER; bid NUMBER; r VARCHAR2(20); exp DATE;
 BEGIN
  SELECT role INTO r FROM HMS_User WHERE user_id=:NEW.user_id AND is_active='Y';
  IF r NOT IN ('pharmacist','manager') OR (:NEW.event_kind IN ('ADJUST_ADD','ADJUST_REMOVE') AND r<>'manager') THEN
   RAISE_APPLICATION_ERROR(-20212,'Stock correction role is not authorized.'); END IF;
  SELECT medicine_id,expires_on INTO mid,exp FROM HMS_Medicine_Batch WHERE batch_id=:NEW.batch_id;
  IF mid<>:NEW.medicine_id THEN RAISE_APPLICATION_ERROR(-20212,'Movement medicine mismatch.'); END IF;
  IF :NEW.event_kind IN ('RECEIPT','ADJUST_ADD','RETURN_RESTOCK') AND exp<HMS_Today() THEN
   RAISE_APPLICATION_ERROR(-20212,'Expired stock cannot enter available inventory.'); END IF;
  IF :NEW.dispense_id IS NOT NULL THEN
   SELECT batch_id INTO bid FROM HMS_Dispense WHERE dispense_id=:NEW.dispense_id;
   IF bid<>:NEW.batch_id THEN RAISE_APPLICATION_ERROR(-20212,'Return does not match original dispense batch.'); END IF;
  END IF;
 END BEFORE EACH ROW;
 AFTER STATEMENT IS n NUMBER;
 BEGIN
  SELECT COUNT(*) INTO n FROM HMS_Dispense d WHERE
   NVL((SELECT SUM(s.quantity) FROM HMS_Stock_Event s WHERE s.dispense_id=d.dispense_id AND s.event_kind IN ('RETURN_RESTOCK','RETURN_QUARANTINE')),0)>d.quantity;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20212,'Return exceeds original dispense.'); END IF;
  SELECT COUNT(*) INTO n FROM V_HMS_Batch_Recon WHERE difference<>0;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20212,'Batch movement journal does not reconcile.'); END IF;
  SELECT COUNT(*) INTO n FROM V_HMS_Medicine_Recon WHERE difference<>0;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20212,'Aggregate movement journal does not reconcile.'); END IF;
 END AFTER STATEMENT;
END;
/
CREATE OR REPLACE TRIGGER trg_cc_fin FOR INSERT ON HMS_Fin_Event COMPOUND TRIGGER
 BEFORE EACH ROW IS r VARCHAR2(20); bid NUMBER; k VARCHAR2(20); a NUMBER; s NUMBER; d NUMBER;
 BEGIN
  SELECT role INTO r FROM HMS_User WHERE user_id=:NEW.user_id AND is_active='Y';
  IF r<>'manager' AND (r<>'cashier' OR :NEW.event_kind NOT IN ('REFUND','REFUND_CREDIT') OR :NEW.stock_event_id IS NULL) THEN
   RAISE_APPLICATION_ERROR(-20213,'Cashier refunds require a recorded billed return; other financial corrections require a manager.'); END IF;
  SELECT bill_id INTO bid FROM Bill WHERE bill_id=:NEW.bill_id FOR UPDATE WAIT 5;
  IF :NEW.event_kind='REFUND' THEN
   SELECT bill_id INTO bid FROM Bill_Payment WHERE payment_id=:NEW.payment_id;
   IF bid<>:NEW.bill_id THEN RAISE_APPLICATION_ERROR(-20213,'Refund receipt belongs to another invoice.'); END IF;
  END IF;
  IF :NEW.event_kind='VOID' THEN
   SELECT COUNT(*) INTO s FROM Bill_Payment WHERE bill_id=:NEW.bill_id;
   SELECT COUNT(*) INTO d FROM Bill WHERE bill_id=:NEW.bill_id AND (encounter_id IS NOT NULL OR admission_id IS NOT NULL);
   IF s+d>0 THEN RAISE_APPLICATION_ERROR(-20213,'Only unpaid administrative invoices can be voided.'); END IF;
  END IF;
 END BEFORE EACH ROW;
 AFTER STATEMENT IS n NUMBER;
 BEGIN
  SELECT COUNT(*) INTO n FROM HMS_Fin_Event c JOIN HMS_Fin_Event r ON r.event_id=c.related_event_id
   WHERE c.event_kind='REFUND_CREDIT' AND (r.event_kind<>'REFUND' OR r.bill_id<>c.bill_id OR r.amount<>c.amount OR r.user_id<>c.user_id OR NVL(r.stock_event_id,-1)<>NVL(c.stock_event_id,-1));
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20213,'Refund credit pair mismatch.'); END IF;
  SELECT COUNT(*) INTO n FROM HMS_Fin_Event f LEFT JOIN V_HMS_Return_Review r ON r.event_id=f.stock_event_id
   WHERE f.stock_event_id IS NOT NULL AND (r.event_id IS NULL OR r.bill_id<>f.bill_id OR f.event_kind NOT IN ('CREDIT','REFUND_CREDIT','WRITE_OFF','REFUND'));
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20213,'Return correction invoice/kind mismatch.'); END IF;
  SELECT COUNT(*) INTO n FROM V_Invoice_Balances WHERE billed<0 OR paid<0 OR balance<0 OR billed>999999999.99 OR (void_count>0 AND (billed<>0 OR paid<>0));
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20213,'Financial correction exceeds invoice bounds.'); END IF;
  SELECT COUNT(*) INTO n FROM Bill_Payment p WHERE NVL((SELECT SUM(f.amount) FROM HMS_Fin_Event f WHERE f.payment_id=p.payment_id AND f.event_kind='REFUND'),0)>p.amount;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20213,'Refund exceeds original receipt.'); END IF;
  SELECT COUNT(*) INTO n FROM V_HMS_Return_Review WHERE remaining_credit<0;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20213,'Return was credited beyond original-price value.'); END IF;
 END AFTER STATEMENT;
END;
/
-- Freeze original charges after ANY corrective history, including a full refund.
CREATE OR REPLACE TRIGGER trg_cc_item BEFORE INSERT OR UPDATE OR DELETE ON Bill_Item FOR EACH ROW
DECLARE n NUMBER; bid NUMBER;
BEGIN
 IF DELETING THEN bid:=:OLD.bill_id; ELSE bid:=:NEW.bill_id; END IF;
 SELECT COUNT(*) INTO n FROM HMS_Fin_Event WHERE bill_id=bid;
 IF n>0 THEN RAISE_APPLICATION_ERROR(-20213,'Original invoice items are locked after a correction.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_cc_base BEFORE UPDATE OF consultation_charge,room_charge,medicine_charge ON Bill FOR EACH ROW
DECLARE n NUMBER;
BEGIN
 IF :OLD.consultation_charge<>:NEW.consultation_charge OR :OLD.room_charge<>:NEW.room_charge OR :OLD.medicine_charge<>:NEW.medicine_charge THEN
  SELECT COUNT(*) INTO n FROM HMS_Fin_Event WHERE bill_id=:OLD.bill_id;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20213,'Original invoice charges are locked after a correction.'); END IF;
 END IF;
END;
/
ALTER TRIGGER trg_bill_payment_guard COMPILE;
-- Publish readiness only after all read-only postflight assertions pass.
@@../12_correction_invariants.sql
UPDATE HMS_Settings SET correction_version=1 WHERE singleton=1;
COMMIT;
@@../11_corrections_verification.sql
PROMPT 008 installed. Reapply restricted runtime grants10, then run verification11.
