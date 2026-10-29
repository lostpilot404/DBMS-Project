-- Shared fresh/upgrade installer. Run ONLY via fresh 01 or migration 006.
-- Oracle 12c+. All writers stopped. DDL commits; this is not rerunnable/atomic.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
CREATE TABLE HMS_Settings (
 singleton NUMBER(1) PRIMARY KEY CHECK (singleton = 1),
 schema_version NUMBER(3) NOT NULL,
 hospital_timezone VARCHAR2(64) NOT NULL
);
INSERT INTO HMS_Settings VALUES (1, 0, 'Asia/Kolkata');
CREATE TABLE HMS_Write_Mutex (mutex_id NUMBER(1) PRIMARY KEY CHECK (mutex_id = 1));
INSERT INTO HMS_Write_Mutex VALUES (1);
COMMIT;
ALTER TABLE Bill ADD (notes VARCHAR2(300));
ALTER TABLE Bill_Payment ADD (recorded_timezone VARCHAR2(32) DEFAULT 'LEGACY_UNKNOWN' NOT NULL);
CREATE OR REPLACE TRIGGER trg_payment_clock
BEFORE INSERT ON Bill_Payment FOR EACH ROW
BEGIN
 :NEW.recorded_at:=SYS_EXTRACT_UTC(SYSTIMESTAMP);
 :NEW.recorded_timezone:='UTC';
END;
/
ALTER TABLE Bill_Item ADD CONSTRAINT ck_item_demo_limit CHECK (quantity <= 100000 AND line_total <= 99999999.99);
ALTER TABLE Bill_Payment ADD CONSTRAINT ck_payment_demo_limit CHECK (amount <= 99999999.99);
ALTER TABLE Admission MODIFY (admission_date DEFAULT NULL);
ALTER TABLE Bill MODIFY (bill_date DEFAULT NULL);
ALTER TABLE Prescription MODIFY (prescription_date DEFAULT NULL);
CREATE OR REPLACE FUNCTION HMS_Today RETURN DATE AUTHID DEFINER IS
 v_zone HMS_Settings.hospital_timezone%TYPE;
 v_day DATE;
BEGIN
 SELECT hospital_timezone INTO v_zone FROM HMS_Settings WHERE singleton = 1;
 SELECT TRUNC(CAST(SYSTIMESTAMP AT TIME ZONE v_zone AS DATE)) INTO v_day FROM dual;
 RETURN v_day;
END;
/
-- One row serializes writes BEFORE any entity row/unique-index locks. Deliberate
-- academic throughput tradeoff; bounded waits; held until COMMIT/ROLLBACK.
CREATE OR REPLACE TRIGGER trg_lock_department
BEFORE INSERT OR UPDATE OR DELETE ON Department
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_doctor
BEFORE INSERT OR UPDATE OR DELETE ON Doctor
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_patient
BEFORE INSERT OR UPDATE OR DELETE ON Patient
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_appointment
BEFORE INSERT OR UPDATE OR DELETE ON Appointment
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_room
BEFORE INSERT OR UPDATE OR DELETE ON Room
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_admission
BEFORE INSERT OR UPDATE OR DELETE ON Admission
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_admission_room_stay
BEFORE INSERT OR UPDATE OR DELETE ON Admission_Room_Stay
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_medicine
BEFORE INSERT OR UPDATE OR DELETE ON Medicine
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_prescription
BEFORE INSERT OR UPDATE OR DELETE ON Prescription
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_bill
BEFORE INSERT OR UPDATE OR DELETE ON Bill
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_bill_item
BEFORE INSERT OR UPDATE OR DELETE ON Bill_Item
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE TRIGGER trg_lock_bill_payment
BEFORE INSERT OR UPDATE OR DELETE ON Bill_Payment
DECLARE v_lock NUMBER;
BEGIN
 SELECT mutex_id INTO v_lock FROM HMS_Write_Mutex WHERE mutex_id = 1 FOR UPDATE WAIT 5;
END;
/
CREATE OR REPLACE VIEW V_Invoice_Balances AS
SELECT b.bill_id, b.patient_id, b.bill_date, b.notes,
 b.consultation_charge, b.room_charge, b.medicine_charge,
 b.payment_status AS legacy_status, b.total_amount AS legacy_charges,
 NVL(i.item_total,0) AS item_total,
 b.total_amount + NVL(i.item_total,0) AS billed,
 NVL(p.paid_total,0) AS paid,
 b.total_amount + NVL(i.item_total,0) - NVL(p.paid_total,0) AS balance,
 CASE WHEN b.total_amount + NVL(i.item_total,0) = NVL(p.paid_total,0) THEN 'Paid'
      WHEN NVL(p.paid_total,0) = 0 THEN 'Unpaid' ELSE 'Partial' END AS ledger_status
FROM Bill b
LEFT JOIN (SELECT bill_id, SUM(line_total) item_total FROM Bill_Item GROUP BY bill_id) i ON i.bill_id=b.bill_id
LEFT JOIN (SELECT bill_id, SUM(amount) paid_total FROM Bill_Payment GROUP BY bill_id) p ON p.bill_id=b.bill_id;

CREATE OR REPLACE TRIGGER trg_bill_item_guard
BEFORE INSERT OR UPDATE OR DELETE ON Bill_Item
FOR EACH ROW
DECLARE
    v_bill NUMBER;
    v_lock NUMBER;
    v_payments NUMBER;
BEGIN
    IF UPDATING AND :OLD.bill_id <> :NEW.bill_id THEN
        RAISE_APPLICATION_ERROR(-20031, 'Item ownership is immutable.');
    END IF;
    IF DELETING THEN v_bill := :OLD.bill_id; ELSE v_bill := :NEW.bill_id; END IF;
    SELECT bill_id INTO v_lock FROM Bill WHERE bill_id = v_bill FOR UPDATE WAIT 5;
    SELECT COUNT(*) INTO v_payments FROM Bill_Payment WHERE bill_id = v_bill;
    IF v_payments > 0 THEN RAISE_APPLICATION_ERROR(-20031, 'Charges cannot change after payment.'); END IF;
END;
/

CREATE OR REPLACE TRIGGER trg_bill_charge_guard
BEFORE UPDATE OF consultation_charge, room_charge, medicine_charge ON Bill
FOR EACH ROW
DECLARE v_payments NUMBER;
BEGIN
    IF :OLD.consultation_charge <> :NEW.consultation_charge OR :OLD.room_charge <> :NEW.room_charge
       OR :OLD.medicine_charge <> :NEW.medicine_charge THEN
        SELECT COUNT(*) INTO v_payments FROM Bill_Payment WHERE bill_id = :OLD.bill_id;
        IF v_payments > 0 THEN RAISE_APPLICATION_ERROR(-20031, 'Charges cannot change after payment.'); END IF;
    END IF;
END;
/

-- Payment rows are append-only. Check totals after the DML statement, avoiding
-- a query of the mutating payment table. The bill row locks serialize inserts.
CREATE OR REPLACE TRIGGER trg_bill_payment_guard
FOR INSERT OR UPDATE OR DELETE ON Bill_Payment
COMPOUND TRIGGER
    TYPE bill_map IS TABLE OF NUMBER INDEX BY VARCHAR2(10);
    g_bills bill_map;
    BEFORE EACH ROW IS
        v_lock NUMBER;
        v_key VARCHAR2(10);
    BEGIN
        IF UPDATING OR DELETING THEN
            RAISE_APPLICATION_ERROR(-20032, 'Payment history cannot be changed or deleted.');
        END IF;
        SELECT bill_id INTO v_lock FROM Bill WHERE bill_id = :NEW.bill_id FOR UPDATE WAIT 5;
        v_key := LPAD(TO_CHAR(:NEW.bill_id, 'FM9999999990'), 10, '0');
        g_bills(v_key) := :NEW.bill_id;
    END BEFORE EACH ROW;
    AFTER STATEMENT IS
        v_key VARCHAR2(10);
        v_bill NUMBER;
        v_total NUMBER;
        v_paid NUMBER;
    BEGIN
        v_key := g_bills.FIRST;
        WHILE v_key IS NOT NULL LOOP
            v_bill := g_bills(v_key);
            SELECT billed, paid INTO v_total, v_paid FROM V_Invoice_Balances WHERE bill_id = v_bill;
            IF v_paid > v_total THEN RAISE_APPLICATION_ERROR(-20033, 'Payment exceeds outstanding balance.'); END IF;
            v_key := g_bills.NEXT(v_key);
        END LOOP;
    END AFTER STATEMENT;
END trg_bill_payment_guard;
/


-- Private state cannot be set by runtime SQL. Never grant this package to the
-- runtime user. A schema owner/DBA remains privileged (can disable any trigger).
CREATE OR REPLACE PACKAGE HMS_Internal AUTHID DEFINER AS
 FUNCTION projecting RETURN BOOLEAN;
 PROCEDURE sync_admission(p_id NUMBER, p_old_room NUMBER, p_new_room NUMBER,
                          p_old_discharge DATE, p_new_discharge DATE, p_insert BOOLEAN);
END;
/
CREATE OR REPLACE PACKAGE BODY HMS_Internal AS
 g_projection BOOLEAN := FALSE;
 FUNCTION projecting RETURN BOOLEAN IS BEGIN RETURN g_projection; END;
 PROCEDURE sync_admission(p_id NUMBER, p_old_room NUMBER, p_new_room NUMBER,
                          p_old_discharge DATE, p_new_discharge DATE, p_insert BOOLEAN) IS
 v_now TIMESTAMP := SYSTIMESTAMP; -- observation clock; legacy server timezone is not inferred
 BEGIN
  g_projection := TRUE;
  IF p_insert THEN
   INSERT INTO Admission_Room_Stay(admission_id,room_id,started_at,is_active,source)
   VALUES(p_id,p_new_room,v_now,'Y','LIVE');
   UPDATE Room SET availability_status='Occupied' WHERE room_id=p_new_room;
  ELSIF p_old_discharge IS NULL AND (p_new_discharge IS NOT NULL OR p_old_room<>p_new_room) THEN
   UPDATE Admission_Room_Stay SET is_active='N', ended_at=v_now
    WHERE admission_id=p_id AND room_id=p_old_room AND is_active='Y';
   IF SQL%ROWCOUNT<>1 THEN RAISE_APPLICATION_ERROR(-20028,'Missing current room observation.'); END IF;
   UPDATE Room SET availability_status='Available' WHERE room_id=p_old_room;
   IF p_new_discharge IS NULL THEN
    INSERT INTO Admission_Room_Stay(admission_id,room_id,started_at,is_active,source)
    VALUES(p_id,p_new_room,v_now,'Y','LIVE');
    UPDATE Room SET availability_status='Occupied' WHERE room_id=p_new_room;
   END IF;
  END IF;
  g_projection := FALSE;
 EXCEPTION WHEN OTHERS THEN g_projection:=FALSE; RAISE;
 END;
END;
/
CREATE OR REPLACE TRIGGER trg_stay_write_guard
BEFORE INSERT OR UPDATE OR DELETE ON Admission_Room_Stay
FOR EACH ROW
BEGIN
 IF NOT HMS_Internal.projecting THEN
  RAISE_APPLICATION_ERROR(-20040,'Room history is managed only by Admission mutations.');
 END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_room_write_guard
BEFORE INSERT OR UPDATE ON Room
FOR EACH ROW
DECLARE n NUMBER;
BEGIN
 IF NOT HMS_Internal.projecting THEN
  IF :NEW.availability_status='Occupied' THEN
   IF INSERTING OR :OLD.availability_status<>'Occupied' THEN
    RAISE_APPLICATION_ERROR(-20040,'Occupancy is managed by Admission.');
   END IF;
  END IF;
  SELECT COUNT(*) INTO n FROM Admission WHERE room_id=:NEW.room_id AND discharge_date IS NULL;
  IF (n>0 AND :NEW.availability_status<>'Occupied') OR (n=0 AND :NEW.availability_status='Occupied') THEN
   RAISE_APPLICATION_ERROR(-20040,'Room state must agree with Admission.');
  END IF;
 END IF;
END;
/
-- Replaced by unified sync below. Remove the old independent projection writer.
DROP TRIGGER trg_admission_room_sync;
CREATE OR REPLACE TRIGGER trg_admission_stay_sync
AFTER INSERT OR UPDATE ON Admission
FOR EACH ROW
BEGIN
 HMS_Internal.sync_admission(:NEW.admission_id,:OLD.room_id,:NEW.room_id,
                            :OLD.discharge_date,:NEW.discharge_date,INSERTING);
END;
/
CREATE OR REPLACE TRIGGER trg_admission_room_guard
BEFORE INSERT OR UPDATE ON Admission
FOR EACH ROW
DECLARE
    v_room_status Room.availability_status%TYPE;
BEGIN
    :NEW.admission_date := TRUNC(NVL(:NEW.admission_date,HMS_Today()));
    :NEW.discharge_date := TRUNC(:NEW.discharge_date);
    IF TRUNC(:NEW.admission_date) > HMS_Today()
       OR (:NEW.discharge_date IS NOT NULL AND TRUNC(:NEW.discharge_date) > HMS_Today()) THEN
        RAISE_APPLICATION_ERROR(-20029, 'Admission and discharge dates cannot be in the future.');
    END IF;
    IF INSERTING AND :NEW.discharge_date IS NOT NULL THEN
        RAISE_APPLICATION_ERROR(-20027, 'New admissions must be active.');
    END IF;
    IF UPDATING THEN
        IF :NEW.patient_id <> :OLD.patient_id OR :NEW.admission_date <> :OLD.admission_date THEN
            RAISE_APPLICATION_ERROR(-20027, 'Admission patient and date cannot be changed.');
        END IF;
        IF :OLD.discharge_date IS NOT NULL THEN
            RAISE_APPLICATION_ERROR(-20027, 'A discharged admission is read-only.');
        END IF;
        IF :NEW.discharge_date IS NOT NULL AND :NEW.room_id <> :OLD.room_id THEN
            RAISE_APPLICATION_ERROR(-20027, 'Transfer and discharge must be separate operations.');
        END IF;
    END IF;

    IF :NEW.discharge_date IS NOT NULL AND :NEW.discharge_date < :NEW.admission_date THEN
        RAISE_APPLICATION_ERROR(-20010, 'Discharge date cannot be earlier than admission date.');
    END IF;

    IF :NEW.discharge_date IS NULL THEN
        BEGIN
            SELECT availability_status
              INTO v_room_status
              FROM Room
             WHERE room_id = :NEW.room_id
               FOR UPDATE WAIT 5;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                RAISE_APPLICATION_ERROR(-20011, 'Selected room does not exist.');
        END;

        IF INSERTING THEN
            IF v_room_status <> 'Available' THEN
                RAISE_APPLICATION_ERROR(-20012, 'Selected room is not available.');
            END IF;
        ELSIF :OLD.discharge_date IS NOT NULL OR :OLD.room_id <> :NEW.room_id THEN
            IF v_room_status <> 'Available' THEN
                RAISE_APPLICATION_ERROR(-20012, 'Selected room is not available.');
            END IF;
        ELSIF v_room_status <> 'Occupied' THEN
            RAISE_APPLICATION_ERROR(-20013, 'Room status is inconsistent with its active admission.');
        END IF;
    ELSIF UPDATING AND :OLD.discharge_date IS NULL THEN
        SELECT availability_status
          INTO v_room_status
          FROM Room
         WHERE room_id = :OLD.room_id
           FOR UPDATE WAIT 5;
        IF v_room_status <> 'Occupied' THEN
            RAISE_APPLICATION_ERROR(-20013, 'Room status is inconsistent with its active admission.');
        END IF;
    END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_appointment_guard
BEFORE INSERT OR UPDATE ON Appointment
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        IF :NEW.status <> 'Scheduled' THEN
            RAISE_APPLICATION_ERROR(-20023, 'A new appointment must start as Scheduled.');
        END IF;
        IF TRUNC(:NEW.appointment_date) < HMS_Today() THEN
            RAISE_APPLICATION_ERROR(-20022, 'A scheduled appointment cannot be in the past.');
        END IF;
    END IF;

    IF UPDATING THEN
        IF :NEW.status <> :OLD.status AND
           (:NEW.patient_id <> :OLD.patient_id OR :NEW.doctor_id <> :OLD.doctor_id
            OR :NEW.appointment_date <> :OLD.appointment_date
            OR :NEW.appointment_time <> :OLD.appointment_time
            OR :NEW.duration_minutes <> :OLD.duration_minutes) THEN
            RAISE_APPLICATION_ERROR(-20024, 'Change booking and status separately.');
        END IF;
        IF :OLD.status IN ('Completed', 'Cancelled', 'No-show') THEN
            IF :NEW.status <> :OLD.status
               OR :NEW.patient_id <> :OLD.patient_id
               OR :NEW.doctor_id <> :OLD.doctor_id
               OR :NEW.appointment_date <> :OLD.appointment_date
               OR :NEW.appointment_time <> :OLD.appointment_time
               OR :NEW.duration_minutes <> :OLD.duration_minutes THEN
                RAISE_APPLICATION_ERROR(-20020, 'Terminal appointment records are read-only history.');
            END IF;
        END IF;

        IF :OLD.status <> 'Scheduled'
           AND (:NEW.patient_id <> :OLD.patient_id
                OR :NEW.doctor_id <> :OLD.doctor_id
                OR :NEW.appointment_date <> :OLD.appointment_date
                OR :NEW.appointment_time <> :OLD.appointment_time
                OR :NEW.duration_minutes <> :OLD.duration_minutes) THEN
            RAISE_APPLICATION_ERROR(-20024, 'Only a scheduled appointment can be rescheduled.');
        END IF;

        IF :NEW.status <> :OLD.status
           AND NOT (
               (:OLD.status = 'Scheduled'
                    AND :NEW.status IN ('Checked In', 'Cancelled', 'No-show'))
               OR (:OLD.status = 'Checked In' AND :NEW.status = 'Waiting')
               OR (:OLD.status = 'Waiting' AND :NEW.status = 'In Consultation')
               OR (:OLD.status = 'In Consultation' AND :NEW.status = 'Completed')
           ) THEN
            RAISE_APPLICATION_ERROR(-20024, 'The requested appointment status transition is not allowed.');
        END IF;

        IF :NEW.status = 'Scheduled'
           AND TRUNC(:NEW.appointment_date) < HMS_Today() THEN
            RAISE_APPLICATION_ERROR(-20022, 'A scheduled appointment cannot be in the past.');
        END IF;
        IF :OLD.status = 'Scheduled' AND :NEW.status = 'Checked In'
           AND TRUNC(:NEW.appointment_date) <> HMS_Today() THEN
            RAISE_APPLICATION_ERROR(-20025, 'An appointment can be checked in only on its scheduled date.');
        END IF;
        IF :OLD.status = 'Scheduled' AND :NEW.status = 'No-show'
           AND TRUNC(:NEW.appointment_date) >= HMS_Today() THEN
            RAISE_APPLICATION_ERROR(-20026, 'An appointment can be marked No-show only after its date has passed.');
        END IF;
    END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_appt_overlap
FOR INSERT OR UPDATE ON Appointment
COMPOUND TRIGGER
 AFTER STATEMENT IS
  n NUMBER;
 BEGIN
  SELECT COUNT(*) INTO n FROM Appointment a JOIN Appointment b
   ON a.appointment_id<b.appointment_id AND a.appointment_date=b.appointment_date
   AND (a.doctor_id=b.doctor_id OR a.patient_id=b.patient_id)
   WHERE a.status IN ('Scheduled','Checked In','Waiting','In Consultation')
     AND b.status IN ('Scheduled','Checked In','Waiting','In Consultation')
     AND (TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(a.appointment_time,4,2)))
       < (TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(b.appointment_time,4,2))+b.duration_minutes)
     AND (TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(a.appointment_time,4,2))+a.duration_minutes)
       > (TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(b.appointment_time,4,2)));
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20030,'Doctor or patient appointment intervals overlap.'); END IF;
 END AFTER STATEMENT;
END;
/
CREATE OR REPLACE TRIGGER trg_patient_date
BEFORE INSERT OR UPDATE ON Patient
FOR EACH ROW
BEGIN
 :NEW.date_of_birth:=TRUNC(:NEW.date_of_birth);
 IF :NEW.date_of_birth>HMS_Today() THEN RAISE_APPLICATION_ERROR(-20041,'Date cannot be in the hospital future.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_prescription_date
BEFORE INSERT OR UPDATE ON Prescription
FOR EACH ROW
BEGIN
 :NEW.prescription_date:=TRUNC(NVL(:NEW.prescription_date,HMS_Today()));
 IF :NEW.prescription_date>HMS_Today() THEN RAISE_APPLICATION_ERROR(-20041,'Date cannot be in the hospital future.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_bill_date
BEFORE INSERT OR UPDATE ON Bill
FOR EACH ROW
BEGIN
 :NEW.bill_date:=TRUNC(NVL(:NEW.bill_date,HMS_Today()));
 IF :NEW.bill_date>HMS_Today() THEN RAISE_APPLICATION_ERROR(-20041,'Date cannot be in the hospital future.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_appointment_retain
BEFORE DELETE ON Appointment
FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20042,'Established history cannot be deleted.'); END;
/
CREATE OR REPLACE TRIGGER trg_prescription_retain
BEFORE DELETE ON Prescription
FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20042,'Established history cannot be deleted.'); END;
/
CREATE OR REPLACE TRIGGER trg_bill_retain
BEFORE DELETE ON Bill
FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20042,'Established history cannot be deleted.'); END;
/
CREATE OR REPLACE TRIGGER trg_admission_retain
BEFORE DELETE ON Admission
FOR EACH ROW
BEGIN
 IF :OLD.discharge_date IS NULL THEN RAISE_APPLICATION_ERROR(-20014,'Discharge active admission first.'); END IF;
 RAISE_APPLICATION_ERROR(-20042,'Established history cannot be deleted.');
END;
/
CREATE OR REPLACE TRIGGER trg_bill_metadata_guard
BEFORE UPDATE ON Bill
FOR EACH ROW
BEGIN
 IF :OLD.bill_date<>:NEW.bill_date OR :OLD.payment_status<>:NEW.payment_status THEN
  RAISE_APPLICATION_ERROR(-20043,'Invoice date and legacy status are immutable; edit notes only.');
 END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_item_total_guard
FOR INSERT OR UPDATE OR DELETE ON Bill_Item
COMPOUND TRIGGER
 AFTER STATEMENT IS n NUMBER;
 BEGIN
  SELECT COUNT(*) INTO n FROM V_Invoice_Balances WHERE billed>999999999.99;
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20044,'Invoice exceeds supported total.'); END IF;
 END AFTER STATEMENT;
END;
/
CREATE OR REPLACE TRIGGER trg_bill_total_guard
BEFORE INSERT OR UPDATE ON Bill
FOR EACH ROW
DECLARE v_items NUMBER:=0;
BEGIN
 IF UPDATING THEN SELECT NVL(SUM(line_total),0) INTO v_items FROM Bill_Item WHERE bill_id=:OLD.bill_id; END IF;
 IF :NEW.consultation_charge+:NEW.room_charge+:NEW.medicine_charge+v_items>999999999.99 THEN
  RAISE_APPLICATION_ERROR(-20044,'Invoice exceeds supported total.');
 END IF;
END;
/
CREATE UNIQUE INDEX uq_payment_request_norm ON Bill_Payment(LOWER(idempotency_key));

-- FK indexes avoid unnecessary parent/child lock amplification.
CREATE INDEX ix_doctor_department ON Doctor(department_id);
CREATE INDEX ix_appt_patient_day ON Appointment(patient_id,appointment_date);
CREATE INDEX ix_admission_patient ON Admission(patient_id);
CREATE INDEX ix_admission_room ON Admission(room_id);
CREATE INDEX ix_rx_patient ON Prescription(patient_id);
CREATE INDEX ix_rx_doctor ON Prescription(doctor_id);
CREATE INDEX ix_rx_medicine ON Prescription(medicine_id);
CREATE INDEX ix_bill_patient ON Bill(patient_id);
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM user_objects WHERE status='INVALID';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20140,'Invalid objects: inspect USER_ERRORS; keep writers stopped.'); END IF;
 COMMIT;
END;
/

@@04_verification.sql
