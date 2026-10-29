-- Additive multi-user/clinical operations extension of v6. Oracle12c+ owner only.
-- Stop ALL writers, back up, rehearse disposable schema. DDL commits implicitly.
-- No old accounts, clinical diagnoses, dispensing or receipt facts are fabricated.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM HMS_Settings WHERE schema_version=6;
 IF n<>1 THEN RAISE_APPLICATION_ERROR(-20200,'Complete v6 repair first.'); END IF;
 SELECT COUNT(*) INTO n FROM user_tables WHERE table_name IN ('HMS_USER','HMS_STAFF','HMS_SESSION','HMS_AUDIT');
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20200,'007 already/partly applied; stop and inspect.'); END IF;
 SELECT COUNT(*) INTO n FROM user_tab_cols WHERE table_name='HMS_SETTINGS' AND column_name='MULTIUSER_VERSION';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20200,'007 marker column exists; do not rerun partial DDL.'); END IF;
 SELECT COUNT(*) INTO n FROM user_objects WHERE status='INVALID';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20200,'Invalid baseline objects.'); END IF;
END;
/
@@../06_invariant_checks.sql
ALTER TABLE HMS_Settings ADD (multiuser_version NUMBER(2) DEFAULT 0 NOT NULL, consultation_fee NUMBER(10,2) DEFAULT 0 NOT NULL CHECK(consultation_fee>=0));
CREATE TABLE HMS_Staff (
 staff_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 full_name VARCHAR2(150) NOT NULL, staff_kind VARCHAR2(30) NOT NULL,
 phone VARCHAR2(20), is_active CHAR(1) DEFAULT 'Y' NOT NULL CHECK(is_active IN ('Y','N'))
);
CREATE TABLE HMS_User (
 user_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 username VARCHAR2(100) NOT NULL UNIQUE, password_hash VARCHAR2(300) NOT NULL,
 role VARCHAR2(20) NOT NULL CHECK(role IN ('manager','doctor','patient','receptionist','nurse','pharmacist','cashier','lab','maintenance')),
 patient_id NUMBER(10) UNIQUE REFERENCES Patient(patient_id),
 doctor_id NUMBER(10) UNIQUE REFERENCES Doctor(doctor_id),
 staff_id NUMBER(10) UNIQUE REFERENCES HMS_Staff(staff_id),
 is_active CHAR(1) DEFAULT 'Y' NOT NULL CHECK(is_active IN ('Y','N')),
 CONSTRAINT ck_user_link CHECK ((role='patient' AND patient_id IS NOT NULL AND doctor_id IS NULL AND staff_id IS NULL) OR
 (role='doctor' AND doctor_id IS NOT NULL AND patient_id IS NULL AND staff_id IS NULL) OR
 (role NOT IN ('patient','doctor') AND staff_id IS NOT NULL AND patient_id IS NULL AND doctor_id IS NULL)),
 CONSTRAINT ck_user_lower CHECK(username=LOWER(username))
);
CREATE TABLE HMS_Session (
 token_hash VARCHAR2(64) PRIMARY KEY,user_id NUMBER(10) NOT NULL REFERENCES HMS_User(user_id),
 csrf_token VARCHAR2(64) NOT NULL,expires_at TIMESTAMP NOT NULL
);
CREATE INDEX ix_session_user ON HMS_Session(user_id);
CREATE INDEX ix_session_expiry ON HMS_Session(expires_at);
CREATE TABLE HMS_Audit (
 audit_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 user_id NUMBER(10) NOT NULL REFERENCES HMS_User(user_id),action VARCHAR2(40) NOT NULL,
 entity VARCHAR2(40) NOT NULL,record_id NUMBER(10) NOT NULL,
 recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL
);
CREATE TABLE HMS_Care_Assignment (
 assignment_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 patient_id NUMBER(10) NOT NULL REFERENCES Patient(patient_id),doctor_id NUMBER(10) NOT NULL REFERENCES Doctor(doctor_id),
 is_active CHAR(1) DEFAULT 'Y' NOT NULL CHECK(is_active IN ('Y','N')), UNIQUE(patient_id,doctor_id)
);
CREATE TABLE HMS_Ward_Assignment (
 assignment_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 admission_id NUMBER(10) NOT NULL REFERENCES Admission(admission_id),user_id NUMBER(10) NOT NULL REFERENCES HMS_User(user_id),
 is_active CHAR(1) DEFAULT 'Y' NOT NULL CHECK(is_active IN ('Y','N')), UNIQUE(admission_id,user_id)
);
CREATE TABLE HMS_Encounter (
 encounter_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 patient_id NUMBER(10) NOT NULL REFERENCES Patient(patient_id),doctor_id NUMBER(10) NOT NULL REFERENCES Doctor(doctor_id),
 appointment_id NUMBER(10) UNIQUE REFERENCES Appointment(appointment_id),admission_id NUMBER(10) REFERENCES Admission(admission_id),
 diagnosis VARCHAR2(1000),clinical_notes VARCHAR2(2000),status VARCHAR2(20) DEFAULT 'Open' NOT NULL CHECK(status IN ('Open','Completed')),
 recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL,
 CHECK(appointment_id IS NULL OR admission_id IS NULL)
);
ALTER TABLE Prescription ADD (encounter_id NUMBER(10) REFERENCES HMS_Encounter(encounter_id),ordered_quantity NUMBER(6) CHECK(ordered_quantity BETWEEN 1 AND 100000));
CREATE TABLE HMS_Observation (
 observation_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 admission_id NUMBER(10) NOT NULL REFERENCES Admission(admission_id),user_id NUMBER(10) NOT NULL REFERENCES HMS_User(user_id),
 observation VARCHAR2(2000) NOT NULL,recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL
);
CREATE TABLE HMS_Test_Catalog (
 test_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 test_name VARCHAR2(150) NOT NULL UNIQUE,fee NUMBER(10,2) DEFAULT 0 NOT NULL CHECK(fee>=0),is_active CHAR(1) DEFAULT 'Y' NOT NULL CHECK(is_active IN ('Y','N'))
);
CREATE TABLE HMS_Test_Order (
 order_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 encounter_id NUMBER(10) NOT NULL REFERENCES HMS_Encounter(encounter_id),test_id NUMBER(10) NOT NULL REFERENCES HMS_Test_Catalog(test_id),
 status VARCHAR2(20) DEFAULT 'Ordered' NOT NULL CHECK(status IN ('Ordered','Resulted')),
 ordered_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL
);
CREATE TABLE HMS_Test_Result (
 result_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 order_id NUMBER(10) NOT NULL UNIQUE REFERENCES HMS_Test_Order(order_id),user_id NUMBER(10) NOT NULL REFERENCES HMS_User(user_id),
 result_text VARCHAR2(2000) NOT NULL,recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL
);
CREATE TABLE HMS_Appointment_Request (
 request_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 patient_id NUMBER(10) NOT NULL REFERENCES Patient(patient_id),doctor_id NUMBER(10) NOT NULL REFERENCES Doctor(doctor_id),
 requested_date DATE NOT NULL,requested_time VARCHAR2(5) NOT NULL,reason VARCHAR2(300),
 status VARCHAR2(20) DEFAULT 'Pending' NOT NULL CHECK(status IN ('Pending','Accepted','Rejected')),
 appointment_id NUMBER(10) REFERENCES Appointment(appointment_id),encounter_id NUMBER(10) REFERENCES HMS_Encounter(encounter_id),
 CHECK(REGEXP_LIKE(requested_time,'^([01][0-9]|2[0-3]):[0-5][0-9]$'))
);
CREATE TABLE HMS_Medicine_Batch (
 batch_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 medicine_id NUMBER(10) NOT NULL REFERENCES Medicine(medicine_id),batch_number VARCHAR2(60) NOT NULL,
 expires_on DATE NOT NULL,quantity NUMBER(10) NOT NULL CHECK(quantity>=0),UNIQUE(medicine_id,batch_number)
);
CREATE TABLE HMS_Dispense (
 dispense_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 prescription_id NUMBER(10) NOT NULL REFERENCES Prescription(prescription_id),batch_id NUMBER(10) NOT NULL REFERENCES HMS_Medicine_Batch(batch_id),
 user_id NUMBER(10) NOT NULL REFERENCES HMS_User(user_id),quantity NUMBER(6) NOT NULL CHECK(quantity BETWEEN 1 AND 100000),
 idempotency_key VARCHAR2(36) NOT NULL UNIQUE,
 recorded_at TIMESTAMP DEFAULT SYS_EXTRACT_UTC(SYSTIMESTAMP) NOT NULL
);
ALTER TABLE Bill ADD (encounter_id NUMBER(10) REFERENCES HMS_Encounter(encounter_id),admission_id NUMBER(10) REFERENCES Admission(admission_id),CONSTRAINT ck_bill_context CHECK(encounter_id IS NULL OR admission_id IS NULL));
CREATE TABLE HMS_Care_Charge (
 charge_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 encounter_id NUMBER(10) NOT NULL REFERENCES HMS_Encounter(encounter_id),source_kind VARCHAR2(20) NOT NULL CHECK(source_kind IN ('Consultation','Dispense','Test')),
 source_id NUMBER(10) NOT NULL,description VARCHAR2(200) NOT NULL,quantity NUMBER(6) NOT NULL CHECK(quantity BETWEEN 1 AND 100000),
 unit_price NUMBER(10,2) NOT NULL CHECK(unit_price>=0),CONSTRAINT ck_care_line_limit CHECK(quantity*unit_price<=99999999.99),bill_item_id NUMBER(10) UNIQUE REFERENCES Bill_Item(item_id),UNIQUE(source_kind,source_id)
);
CREATE TABLE HMS_Maintenance_Task (
 task_id NUMBER(10) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 room_id NUMBER(10) NOT NULL REFERENCES Room(room_id),description VARCHAR2(300) NOT NULL,
 status VARCHAR2(20) DEFAULT 'Open' NOT NULL CHECK(status IN ('Open','InProgress','Completed')),
 created_by NUMBER(10) NOT NULL REFERENCES HMS_User(user_id),completed_by NUMBER(10) REFERENCES HMS_User(user_id)
);
-- Remaining FKs; leading UNIQUE/PK indexes already cover other references.
CREATE INDEX ix_mu_fk_01 ON HMS_Audit(user_id);
CREATE INDEX ix_mu_fk_02 ON HMS_Care_Assignment(doctor_id);
CREATE INDEX ix_mu_fk_03 ON HMS_Ward_Assignment(user_id);
CREATE INDEX ix_mu_fk_04 ON HMS_Encounter(patient_id);
CREATE INDEX ix_mu_fk_05 ON HMS_Encounter(doctor_id);
CREATE INDEX ix_mu_fk_06 ON HMS_Encounter(admission_id);
CREATE INDEX ix_mu_fk_07 ON Prescription(encounter_id);
CREATE INDEX ix_mu_fk_08 ON HMS_Observation(admission_id);
CREATE INDEX ix_mu_fk_09 ON HMS_Observation(user_id);
CREATE INDEX ix_mu_fk_10 ON HMS_Test_Order(encounter_id);
CREATE INDEX ix_mu_fk_11 ON HMS_Test_Order(test_id);
CREATE INDEX ix_mu_fk_12 ON HMS_Test_Result(user_id);
CREATE INDEX ix_mu_fk_13 ON HMS_Appointment_Request(patient_id);
CREATE INDEX ix_mu_fk_14 ON HMS_Appointment_Request(doctor_id);
CREATE INDEX ix_mu_fk_15 ON HMS_Appointment_Request(appointment_id);
CREATE INDEX ix_mu_fk_16 ON HMS_Appointment_Request(encounter_id);
CREATE INDEX ix_mu_fk_17 ON HMS_Dispense(prescription_id);
CREATE INDEX ix_mu_fk_18 ON HMS_Dispense(batch_id);
CREATE INDEX ix_mu_fk_19 ON HMS_Dispense(user_id);
CREATE INDEX ix_mu_fk_20 ON HMS_Care_Charge(encounter_id);
CREATE INDEX ix_mu_fk_21 ON HMS_Maintenance_Task(room_id);
CREATE INDEX ix_mu_fk_22 ON HMS_Maintenance_Task(created_by);
CREATE INDEX ix_mu_fk_23 ON HMS_Maintenance_Task(completed_by);
-- New writes participate in the SAME v6 mutex, never a competing lock order.
CREATE OR REPLACE TRIGGER trg_mu_staff
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Staff
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_user
BEFORE INSERT OR UPDATE OR DELETE ON HMS_User
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_session
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Session
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_audit
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Audit
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_care_assignment
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Care_Assignment
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_ward_assignment
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Ward_Assignment
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_encounter
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Encounter
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_observation
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Observation
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_test_catalog
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Test_Catalog
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_test_order
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Test_Order
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_test_result
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Test_Result
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_appointment_request
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Appointment_Request
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_medicine_batch
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Medicine_Batch
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_dispense
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Dispense
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_care_charge
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Care_Charge
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
CREATE OR REPLACE TRIGGER trg_mu_maintenance_task
BEFORE INSERT OR UPDATE OR DELETE ON HMS_Maintenance_Task
DECLARE n NUMBER;
BEGIN SELECT mutex_id INTO n FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5; END;
/
-- Identity/session retention: accounts deactivate, clinical facts append.
CREATE OR REPLACE TRIGGER trg_mu_account_delete BEFORE DELETE ON HMS_User FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Deactivate accounts; retain authorship.'); END;
/
CREATE OR REPLACE TRIGGER trg_mu_audit_guard BEFORE UPDATE OR DELETE ON HMS_Audit FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Audit events are retained.'); END;
/
CREATE OR REPLACE TRIGGER trg_mu_batch_stock BEFORE UPDATE OF stock_quantity ON Medicine FOR EACH ROW
DECLARE n NUMBER;
BEGIN
 SELECT NVL(SUM(quantity),0) INTO n FROM HMS_Medicine_Batch WHERE medicine_id=:OLD.medicine_id;
 IF :NEW.stock_quantity<n THEN RAISE_APPLICATION_ERROR(-20202,'Stock cannot fall below allocated batch balance.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_mu_bill_context BEFORE UPDATE ON Bill FOR EACH ROW
BEGIN
 IF NVL(:OLD.encounter_id,-1)<>NVL(:NEW.encounter_id,-1) OR NVL(:OLD.admission_id,-1)<>NVL(:NEW.admission_id,-1) THEN
  RAISE_APPLICATION_ERROR(-20201,'Invoice care context is immutable.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_keep_encounter BEFORE DELETE ON HMS_Encounter FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Care history is retained.'); END;
/
CREATE OR REPLACE TRIGGER trg_keep_observation BEFORE DELETE ON HMS_Observation FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Care history is retained.'); END;
/
CREATE OR REPLACE TRIGGER trg_keep_test_order BEFORE DELETE ON HMS_Test_Order FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Care history is retained.'); END;
/
CREATE OR REPLACE TRIGGER trg_keep_test_result BEFORE DELETE ON HMS_Test_Result FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Care history is retained.'); END;
/
CREATE OR REPLACE TRIGGER trg_keep_dispense BEFORE DELETE ON HMS_Dispense FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Care history is retained.'); END;
/
CREATE OR REPLACE TRIGGER trg_keep_care_charge BEFORE DELETE ON HMS_Care_Charge FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Care history is retained.'); END;
/
CREATE OR REPLACE TRIGGER trg_keep_appointment_request BEFORE DELETE ON HMS_Appointment_Request FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Care history is retained.'); END;
/
CREATE OR REPLACE TRIGGER trg_immutable_observation BEFORE UPDATE ON HMS_Observation FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Append-only care fact.'); END;
/
CREATE OR REPLACE TRIGGER trg_immutable_test_result BEFORE UPDATE ON HMS_Test_Result FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Append-only care fact.'); END;
/
CREATE OR REPLACE TRIGGER trg_immutable_dispense BEFORE UPDATE ON HMS_Dispense FOR EACH ROW
BEGIN RAISE_APPLICATION_ERROR(-20201,'Append-only care fact.'); END;
/
CREATE UNIQUE INDEX uq_final_encounter_bill ON Bill(encounter_id);
CREATE UNIQUE INDEX uq_final_admission_bill ON Bill(admission_id);
CREATE UNIQUE INDEX uq_maintenance_inprogress ON HMS_Maintenance_Task(CASE WHEN status='InProgress' THEN room_id END);
CREATE OR REPLACE TRIGGER trg_mu_encounter_guard BEFORE INSERT OR UPDATE ON HMS_Encounter FOR EACH ROW
DECLARE p NUMBER; d NUMBER;
BEGIN
 IF UPDATING THEN
  IF :OLD.status='Completed' OR :OLD.patient_id<>:NEW.patient_id OR :OLD.doctor_id<>:NEW.doctor_id
   OR NVL(:OLD.appointment_id,-1)<>NVL(:NEW.appointment_id,-1) OR NVL(:OLD.admission_id,-1)<>NVL(:NEW.admission_id,-1) THEN
   RAISE_APPLICATION_ERROR(-20201,'Completed encounter/ownership is immutable.'); END IF;
 END IF;
 IF :NEW.appointment_id IS NOT NULL THEN
  SELECT patient_id,doctor_id INTO p,d FROM Appointment WHERE appointment_id=:NEW.appointment_id;
  IF p<>:NEW.patient_id OR d<>:NEW.doctor_id THEN RAISE_APPLICATION_ERROR(-20203,'Encounter appointment mismatch.'); END IF;
 END IF;
 IF :NEW.admission_id IS NOT NULL THEN
  SELECT patient_id INTO p FROM Admission WHERE admission_id=:NEW.admission_id;
  IF p<>:NEW.patient_id THEN RAISE_APPLICATION_ERROR(-20203,'Encounter admission mismatch.'); END IF;
 END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_mu_rx_context BEFORE INSERT OR UPDATE ON Prescription FOR EACH ROW
DECLARE p NUMBER; d NUMBER;
BEGIN
 IF :NEW.encounter_id IS NOT NULL THEN
  SELECT patient_id,doctor_id INTO p,d FROM HMS_Encounter WHERE encounter_id=:NEW.encounter_id;
  IF p<>:NEW.patient_id OR d<>:NEW.doctor_id THEN RAISE_APPLICATION_ERROR(-20203,'Prescription care mismatch.'); END IF;
 END IF;
 IF UPDATING AND :OLD.encounter_id IS NOT NULL THEN RAISE_APPLICATION_ERROR(-20201,'Clinical order is retained; issue a new order.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_mu_charge_guard BEFORE UPDATE ON HMS_Care_Charge FOR EACH ROW
BEGIN
 IF :OLD.bill_item_id IS NOT NULL OR :OLD.encounter_id<>:NEW.encounter_id OR :OLD.source_kind<>:NEW.source_kind
 OR :OLD.source_id<>:NEW.source_id OR :OLD.description<>:NEW.description OR :OLD.quantity<>:NEW.quantity OR :OLD.unit_price<>:NEW.unit_price THEN
 RAISE_APPLICATION_ERROR(-20201,'Care charge source and billed links are retained.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_mu_discharge_guard BEFORE UPDATE OF discharge_date ON Admission FOR EACH ROW
DECLARE n NUMBER;
BEGIN
 IF :OLD.discharge_date IS NULL AND :NEW.discharge_date IS NOT NULL THEN
  SELECT COUNT(*) INTO n FROM HMS_Encounter WHERE admission_id=:OLD.admission_id AND status='Open';
  IF n>0 THEN RAISE_APPLICATION_ERROR(-20204,'Complete ward consultations before discharge.'); END IF;
 END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_mu_medicine_guard BEFORE UPDATE OF stock_quantity ON Medicine FOR EACH ROW
DECLARE n NUMBER;
BEGIN
 SELECT NVL(SUM(quantity),0) INTO n FROM HMS_Medicine_Batch WHERE medicine_id=:OLD.medicine_id;
 IF :NEW.stock_quantity<n THEN RAISE_APPLICATION_ERROR(-20202,'Aggregate stock cannot undercut known batch balances.'); END IF;
END;
/
CREATE OR REPLACE TRIGGER trg_mu_bill_context BEFORE INSERT OR UPDATE ON Bill FOR EACH ROW
DECLARE p NUMBER;
BEGIN
 IF UPDATING AND (NVL(:OLD.encounter_id,-1)<>NVL(:NEW.encounter_id,-1) OR NVL(:OLD.admission_id,-1)<>NVL(:NEW.admission_id,-1)) THEN
 RAISE_APPLICATION_ERROR(-20201,'Invoice care context is immutable.'); END IF;
 IF :NEW.encounter_id IS NOT NULL THEN
  SELECT patient_id INTO p FROM HMS_Encounter WHERE encounter_id=:NEW.encounter_id;
  IF p<>:NEW.patient_id THEN RAISE_APPLICATION_ERROR(-20203,'Invoice encounter patient mismatch.'); END IF;
 END IF;
 IF :NEW.admission_id IS NOT NULL THEN
  SELECT patient_id INTO p FROM Admission WHERE admission_id=:NEW.admission_id;
  IF p<>:NEW.patient_id THEN RAISE_APPLICATION_ERROR(-20203,'Invoice admission patient mismatch.'); END IF;
 END IF;
END;
/
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM user_objects WHERE status='INVALID';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20200,'Invalid multi-user objects; inspect USER_ERRORS.'); END IF;
 UPDATE HMS_Settings SET multiuser_version=1 WHERE singleton=1;
 COMMIT;
END;
/
PROMPT 007 installed. Run flask --app app init-manager locally; no default credentials.
