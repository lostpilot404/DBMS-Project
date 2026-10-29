-- Hospital Management System schema (Oracle Database 12c+).
-- Non-destructive: this script does not drop existing objects or data.
-- Run once in a new project schema. It deliberately fails if the tables already exist.
SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

CREATE TABLE Department (
    department_id   NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    department_name VARCHAR2(100) NOT NULL,
    location        VARCHAR2(150) NOT NULL,
    CONSTRAINT pk_department PRIMARY KEY (department_id),
    CONSTRAINT uq_department_name UNIQUE (department_name)
);

CREATE TABLE Doctor (
    doctor_id     NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    doctor_name   VARCHAR2(150) NOT NULL,
    specialization VARCHAR2(120) NOT NULL,
    phone         VARCHAR2(20),
    email         VARCHAR2(254),
    department_id NUMBER(10) NOT NULL,
    CONSTRAINT pk_doctor PRIMARY KEY (doctor_id),
    CONSTRAINT uq_doctor_phone UNIQUE (phone),
    CONSTRAINT uq_doctor_email UNIQUE (email),
    CONSTRAINT fk_doctor_department FOREIGN KEY (department_id)
        REFERENCES Department (department_id)
);

CREATE TABLE Patient (
    patient_id     NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    patient_name   VARCHAR2(150) NOT NULL,
    date_of_birth  DATE NOT NULL,
    gender         CHAR(1) NOT NULL,
    phone          VARCHAR2(20),
    address        VARCHAR2(300),
    blood_group    VARCHAR2(3),
    CONSTRAINT pk_patient PRIMARY KEY (patient_id),
    CONSTRAINT uq_patient_phone UNIQUE (phone),
    CONSTRAINT ck_patient_gender CHECK (gender IN ('M', 'F', 'O')),
    CONSTRAINT ck_patient_blood_group CHECK
        (blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'))
);

CREATE TABLE Appointment (
    appointment_id   NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    patient_id       NUMBER(10) NOT NULL,
    doctor_id        NUMBER(10) NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR2(5) NOT NULL,
    duration_minutes NUMBER(4) DEFAULT 30 NOT NULL,
    status           VARCHAR2(20) DEFAULT 'Scheduled' NOT NULL,
    -- Scheduled, checked-in, waiting, and in-consultation visits reserve a slot.
    -- Completed, cancelled, and no-show appointments remain history and release it.
    active_doctor_id NUMBER(10) GENERATED ALWAYS AS
        (CASE WHEN status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation') THEN doctor_id END) VIRTUAL,
    active_patient_id NUMBER(10) GENERATED ALWAYS AS
        (CASE WHEN status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation') THEN patient_id END) VIRTUAL,
    active_slot_date DATE GENERATED ALWAYS AS
        (CASE WHEN status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation') THEN appointment_date END) VIRTUAL,
    active_slot_time VARCHAR2(5) GENERATED ALWAYS AS
        (CASE WHEN status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation') THEN appointment_time END) VIRTUAL,
    CONSTRAINT pk_appointment PRIMARY KEY (appointment_id),
    CONSTRAINT fk_appointment_patient FOREIGN KEY (patient_id)
        REFERENCES Patient (patient_id),
    CONSTRAINT fk_appointment_doctor FOREIGN KEY (doctor_id)
        REFERENCES Doctor (doctor_id),
    CONSTRAINT ck_appointment_status CHECK
        (status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation',
                    'Completed', 'Cancelled', 'No-show')),
    CONSTRAINT ck_appointment_day CHECK (appointment_date = TRUNC(appointment_date)),
    CONSTRAINT ck_appt_duration CHECK (duration_minutes BETWEEN 1 AND 1440),
    CONSTRAINT ck_appt_end_day CHECK
        ((TO_NUMBER(SUBSTR(appointment_time, 1, 2)) * 60 + TO_NUMBER(SUBSTR(appointment_time, 4, 2)) + duration_minutes) <= 1440),
    CONSTRAINT ck_appointment_time CHECK
        (REGEXP_LIKE(appointment_time, '^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$')),
    CONSTRAINT uq_appointment_doctor_slot UNIQUE
        (active_doctor_id, active_slot_date, active_slot_time),
    CONSTRAINT uq_appointment_patient_slot UNIQUE
        (active_patient_id, active_slot_date, active_slot_time)
);

-- Enforce appointment lifecycle, check-in/no-show timing, and booking immutability
-- at the database boundary. The API applies the same transitions for clearer feedback.
CREATE OR REPLACE TRIGGER trg_appointment_guard
BEFORE INSERT OR UPDATE ON Appointment
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        IF :NEW.status <> 'Scheduled' THEN
            RAISE_APPLICATION_ERROR(-20023, 'A new appointment must start as Scheduled.');
        END IF;
        IF TRUNC(:NEW.appointment_date) < TRUNC(SYSDATE) THEN
            RAISE_APPLICATION_ERROR(-20022, 'A scheduled appointment cannot be in the past.');
        END IF;
    END IF;

    IF UPDATING THEN
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
           AND TRUNC(:NEW.appointment_date) < TRUNC(SYSDATE) THEN
            RAISE_APPLICATION_ERROR(-20022, 'A scheduled appointment cannot be in the past.');
        END IF;
        IF :OLD.status = 'Scheduled' AND :NEW.status = 'Checked In'
           AND TRUNC(:NEW.appointment_date) <> TRUNC(SYSDATE) THEN
            RAISE_APPLICATION_ERROR(-20025, 'An appointment can be checked in only on its scheduled date.');
        END IF;
        IF :OLD.status = 'Scheduled' AND :NEW.status = 'No-show'
           AND TRUNC(:NEW.appointment_date) >= TRUNC(SYSDATE) THEN
            RAISE_APPLICATION_ERROR(-20026, 'An appointment can be marked No-show only after its date has passed.');
        END IF;
    END IF;
END;
/

CREATE INDEX ix_appt_doctor_day ON Appointment (doctor_id, appointment_date);

-- Statement-level validation avoids querying the mutating Appointment table.
-- All affected doctors are locked in sorted order before the overlap query.
-- Requires READ COMMITTED and all doctor FK rows to be present. A deadlock or
-- lock timeout aborts the statement; callers must retry the whole transaction.
CREATE OR REPLACE TRIGGER trg_appt_overlap
FOR INSERT OR UPDATE ON Appointment
COMPOUND TRIGGER
    TYPE doctor_map IS TABLE OF NUMBER INDEX BY VARCHAR2(10);
    g_doctors doctor_map;

    PROCEDURE remember_doctor(p_doctor_id NUMBER) IS
        v_key VARCHAR2(10);
    BEGIN
        IF p_doctor_id IS NOT NULL THEN
            v_key := LPAD(TO_CHAR(p_doctor_id, 'FM9999999990'), 10, '0');
            g_doctors(v_key) := p_doctor_id;
        END IF;
    END;

    AFTER EACH ROW IS
    BEGIN
        IF UPDATING THEN
            remember_doctor(:OLD.doctor_id);
        END IF;
        remember_doctor(:NEW.doctor_id);
    END AFTER EACH ROW;

    AFTER STATEMENT IS
        v_key VARCHAR2(10);
        v_lock NUMBER;
        v_doctor NUMBER;
        v_count NUMBER;
    BEGIN
        v_key := g_doctors.FIRST;
        WHILE v_key IS NOT NULL LOOP
            v_doctor := g_doctors(v_key);
            SELECT doctor_id INTO v_lock FROM Doctor
             WHERE doctor_id = v_doctor FOR UPDATE;
            v_key := g_doctors.NEXT(v_key);
        END LOOP;
        v_key := g_doctors.FIRST;
        WHILE v_key IS NOT NULL LOOP
            v_doctor := g_doctors(v_key);
            SELECT COUNT(*) INTO v_count
              FROM Appointment a JOIN Appointment b
                ON b.doctor_id = a.doctor_id AND b.appointment_date = a.appointment_date
               AND b.appointment_id > a.appointment_id
             WHERE a.doctor_id = v_doctor
               AND a.status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation')
               AND b.status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation')
               AND (TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(a.appointment_time,4,2)))
                   < (TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(b.appointment_time,4,2)) + b.duration_minutes)
               AND (TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(a.appointment_time,4,2)) + a.duration_minutes)
                   > (TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(b.appointment_time,4,2)));
            IF v_count > 0 THEN
                RAISE_APPLICATION_ERROR(-20030, 'Doctor appointment intervals overlap.');
            END IF;
            v_key := g_doctors.NEXT(v_key);
        END LOOP;
    END AFTER STATEMENT;
END trg_appt_overlap;
/

CREATE TABLE Room (
    room_id           NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    room_number       VARCHAR2(20) NOT NULL,
    room_type         VARCHAR2(40) NOT NULL,
    availability_status VARCHAR2(20) DEFAULT 'Available' NOT NULL,
    CONSTRAINT pk_room PRIMARY KEY (room_id),
    CONSTRAINT uq_room_number UNIQUE (room_number),
    CONSTRAINT ck_room_status CHECK
        (availability_status IN ('Available', 'Occupied', 'Maintenance'))
);

CREATE TABLE Admission (
    admission_id  NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    patient_id    NUMBER(10) NOT NULL,
    room_id       NUMBER(10) NOT NULL,
    admission_date DATE DEFAULT SYSDATE NOT NULL,
    discharge_date DATE,
    -- A NULL discharge date denotes an active admission. These virtual columns
    -- make one-active-room and one-active-admission-per-patient rules atomic.
    active_room_id NUMBER(10) GENERATED ALWAYS AS
        (CASE WHEN discharge_date IS NULL THEN room_id END) VIRTUAL,
    active_patient_id NUMBER(10) GENERATED ALWAYS AS
        (CASE WHEN discharge_date IS NULL THEN patient_id END) VIRTUAL,
    CONSTRAINT pk_admission PRIMARY KEY (admission_id),
    CONSTRAINT fk_admission_patient FOREIGN KEY (patient_id)
        REFERENCES Patient (patient_id),
    CONSTRAINT fk_admission_room FOREIGN KEY (room_id)
        REFERENCES Room (room_id),
    CONSTRAINT ck_admission_dates CHECK
        (discharge_date IS NULL OR discharge_date >= admission_date),
    CONSTRAINT uq_admission_active_room UNIQUE (active_room_id),
    CONSTRAINT uq_admission_active_patient UNIQUE (active_patient_id)
);

-- Room assignment observations; legacy rows have unknown historical times.
CREATE TABLE Admission_Room_Stay (
    stay_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    admission_id NUMBER(10) NOT NULL,
    room_id NUMBER(10) NOT NULL,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    is_active CHAR(1) NOT NULL,
    source VARCHAR2(10) NOT NULL,
    recorded_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    active_admission_id NUMBER(10) GENERATED ALWAYS AS
        (CASE WHEN is_active = 'Y' THEN admission_id END) VIRTUAL,
    active_room_id NUMBER(10) GENERATED ALWAYS AS
        (CASE WHEN is_active = 'Y' THEN room_id END) VIRTUAL,
    CONSTRAINT pk_adm_room_stay PRIMARY KEY (stay_id),
    CONSTRAINT fk_stay_admission FOREIGN KEY (admission_id) REFERENCES Admission (admission_id),
    CONSTRAINT fk_stay_room FOREIGN KEY (room_id) REFERENCES Room (room_id),
    CONSTRAINT ck_stay_active CHECK (is_active IN ('Y','N')),
    CONSTRAINT ck_stay_source CHECK (source IN ('LIVE','LEGACY')),
    CONSTRAINT ck_stay_dates CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at),
    CONSTRAINT ck_stay_shape CHECK ((is_active = 'Y' AND ended_at IS NULL) OR is_active = 'N'),
    CONSTRAINT ck_stay_live CHECK (source = 'LEGACY' OR (started_at IS NOT NULL AND (is_active = 'Y' OR ended_at IS NOT NULL))),
    CONSTRAINT uq_stay_active_adm UNIQUE (active_admission_id),
    CONSTRAINT uq_stay_active_room UNIQUE (active_room_id)
);
CREATE INDEX ix_stay_admission ON Admission_Room_Stay (admission_id);
CREATE INDEX ix_stay_room ON Admission_Room_Stay (room_id);

CREATE TABLE Medicine (
    medicine_id   NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    medicine_name VARCHAR2(150) NOT NULL,
    manufacturer  VARCHAR2(150),
    price         NUMBER(10,2) DEFAULT 0 NOT NULL,
    stock_quantity NUMBER(10) DEFAULT 0 NOT NULL,
    CONSTRAINT pk_medicine PRIMARY KEY (medicine_id),
    CONSTRAINT ck_medicine_price CHECK (price >= 0),
    CONSTRAINT ck_medicine_stock CHECK (stock_quantity >= 0)
);

CREATE TABLE Prescription (
    prescription_id   NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    patient_id        NUMBER(10) NOT NULL,
    doctor_id         NUMBER(10) NOT NULL,
    medicine_id       NUMBER(10) NOT NULL,
    dosage            VARCHAR2(200) NOT NULL,
    duration          VARCHAR2(100) NOT NULL,
    prescription_date DATE DEFAULT SYSDATE NOT NULL,
    CONSTRAINT pk_prescription PRIMARY KEY (prescription_id),
    CONSTRAINT fk_prescription_patient FOREIGN KEY (patient_id)
        REFERENCES Patient (patient_id),
    CONSTRAINT fk_prescription_doctor FOREIGN KEY (doctor_id)
        REFERENCES Doctor (doctor_id),
    CONSTRAINT fk_prescription_medicine FOREIGN KEY (medicine_id)
        REFERENCES Medicine (medicine_id)
);

CREATE TABLE Bill (
    bill_id             NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    patient_id          NUMBER(10) NOT NULL,
    bill_date           DATE DEFAULT SYSDATE NOT NULL,
    consultation_charge NUMBER(10,2) DEFAULT 0 NOT NULL,
    room_charge         NUMBER(10,2) DEFAULT 0 NOT NULL,
    medicine_charge     NUMBER(10,2) DEFAULT 0 NOT NULL,
    -- Computed in Oracle so the displayed total can never drift from charges.
    -- One extra integer digit accommodates the sum of three NUMBER(10,2) charges.
    total_amount        NUMBER(11,2) GENERATED ALWAYS AS
        (consultation_charge + room_charge + medicine_charge) VIRTUAL,
    payment_status      VARCHAR2(20) DEFAULT 'Pending' NOT NULL,
    CONSTRAINT pk_bill PRIMARY KEY (bill_id),
    CONSTRAINT fk_bill_patient FOREIGN KEY (patient_id)
        REFERENCES Patient (patient_id),
    CONSTRAINT ck_bill_consultation_charge CHECK (consultation_charge >= 0),
    CONSTRAINT ck_bill_room_charge CHECK (room_charge >= 0),
    CONSTRAINT ck_bill_medicine_charge CHECK (medicine_charge >= 0),
    CONSTRAINT ck_bill_total CHECK (total_amount >= 0),
    CONSTRAINT ck_bill_payment_status CHECK (payment_status IN ('Paid', 'Pending'))
);

-- Additional itemized charges and actual payment events. The three legacy Bill
-- categories remain the opening charge basis; Paid/Pending is not a payment.
CREATE TABLE Bill_Item (
    item_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    bill_id NUMBER(10) NOT NULL,
    description VARCHAR2(200) NOT NULL,
    quantity NUMBER(8) NOT NULL,
    unit_price NUMBER(10,2) NOT NULL,
    line_total NUMBER(18,2) GENERATED ALWAYS AS (quantity * unit_price) VIRTUAL,
    CONSTRAINT pk_bill_item PRIMARY KEY (item_id),
    CONSTRAINT fk_item_bill FOREIGN KEY (bill_id) REFERENCES Bill (bill_id),
    CONSTRAINT ck_item_quantity CHECK (quantity BETWEEN 1 AND 99999999),
    CONSTRAINT ck_item_price CHECK (unit_price >= 0)
);
CREATE INDEX ix_item_bill ON Bill_Item (bill_id);

CREATE TABLE Bill_Payment (
    payment_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    bill_id NUMBER(10) NOT NULL,
    amount NUMBER(11,2) NOT NULL,
    payment_method VARCHAR2(20) NOT NULL,
    reference VARCHAR2(100),
    idempotency_key VARCHAR2(36) NOT NULL,
    recorded_at TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_bill_payment PRIMARY KEY (payment_id),
    CONSTRAINT uq_payment_request UNIQUE (idempotency_key),
    CONSTRAINT fk_payment_bill FOREIGN KEY (bill_id) REFERENCES Bill (bill_id),
    CONSTRAINT ck_payment_amount CHECK (amount > 0),
    CONSTRAINT ck_payment_method CHECK (payment_method IN ('Cash', 'Card', 'Transfer', 'Other'))
);
CREATE INDEX ix_payment_bill ON Bill_Payment (bill_id);

-- Items are editable only before the first payment. Serialize all invoice
-- changes on the same parent row; direct SQL follows the same protocol.
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
    SELECT bill_id INTO v_lock FROM Bill WHERE bill_id = v_bill FOR UPDATE;
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
        SELECT bill_id INTO v_lock FROM Bill WHERE bill_id = :NEW.bill_id FOR UPDATE;
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
            SELECT b.total_amount + NVL((SELECT SUM(i.line_total) FROM Bill_Item i WHERE i.bill_id = b.bill_id), 0)
              INTO v_total FROM Bill b WHERE b.bill_id = v_bill;
            SELECT NVL(SUM(amount), 0) INTO v_paid FROM Bill_Payment WHERE bill_id = v_bill;
            IF v_paid > v_total THEN RAISE_APPLICATION_ERROR(-20033, 'Payment exceeds outstanding balance.'); END IF;
            v_key := g_bills.NEXT(v_key);
        END LOOP;
    END AFTER STATEMENT;
END trg_bill_payment_guard;
/

-- Bill and prescription ownership is immutable after creation.
CREATE OR REPLACE TRIGGER trg_bill_patient_guard
BEFORE UPDATE OF patient_id ON Bill
FOR EACH ROW
BEGIN
    IF :NEW.patient_id <> :OLD.patient_id THEN
        RAISE_APPLICATION_ERROR(-20019, 'Patient ownership cannot be changed.');
    END IF;
END;
/

CREATE OR REPLACE TRIGGER trg_rx_patient_guard
BEFORE UPDATE OF patient_id ON Prescription
FOR EACH ROW
BEGIN
    IF :NEW.patient_id <> :OLD.patient_id THEN
        RAISE_APPLICATION_ERROR(-20019, 'Patient ownership cannot be changed.');
    END IF;
END;
/

-- Admission guard: serialize room assignment with a row lock and reject unavailable rooms.
-- Unique virtual-column constraints above are a second line of defense against races.
CREATE OR REPLACE TRIGGER trg_admission_room_guard
BEFORE INSERT OR UPDATE ON Admission
FOR EACH ROW
DECLARE
    v_room_status Room.availability_status%TYPE;
BEGIN
    IF TRUNC(:NEW.admission_date) > TRUNC(SYSDATE)
       OR (:NEW.discharge_date IS NOT NULL AND TRUNC(:NEW.discharge_date) > TRUNC(SYSDATE)) THEN
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
               FOR UPDATE;
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
           FOR UPDATE;
        IF v_room_status <> 'Occupied' THEN
            RAISE_APPLICATION_ERROR(-20013, 'Room status is inconsistent with its active admission.');
        END IF;
    END IF;
END;
/

-- Keep Room availability synchronized transactionally with Admission inserts,
-- room changes, and discharge-date changes. A failed statement rolls both back.
CREATE OR REPLACE TRIGGER trg_admission_room_sync
AFTER INSERT OR UPDATE ON Admission
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        IF :NEW.discharge_date IS NULL THEN
            UPDATE Room
               SET availability_status = 'Occupied'
             WHERE room_id = :NEW.room_id;
        END IF;
    ELSIF UPDATING THEN
        IF :OLD.discharge_date IS NULL AND :NEW.discharge_date IS NOT NULL THEN
            UPDATE Room
               SET availability_status = 'Available'
             WHERE room_id = :OLD.room_id;
        ELSIF :OLD.discharge_date IS NOT NULL AND :NEW.discharge_date IS NULL THEN
            UPDATE Room
               SET availability_status = 'Occupied'
             WHERE room_id = :NEW.room_id;
        ELSIF :OLD.discharge_date IS NULL AND :NEW.discharge_date IS NULL
          AND :OLD.room_id <> :NEW.room_id THEN
            UPDATE Room
               SET availability_status = 'Available'
             WHERE room_id = :OLD.room_id;
            UPDATE Room
               SET availability_status = 'Occupied'
             WHERE room_id = :NEW.room_id;
        END IF;
    END IF;
END;
/

-- Admission is the write boundary. The room history and existing occupancy
-- triggers participate in the same Oracle statement/transaction.
CREATE OR REPLACE TRIGGER trg_admission_stay_sync
AFTER INSERT OR UPDATE ON Admission
FOR EACH ROW
DECLARE
    v_now TIMESTAMP := SYSTIMESTAMP;
BEGIN
    IF INSERTING THEN
        IF :NEW.discharge_date IS NULL THEN
            INSERT INTO Admission_Room_Stay (admission_id, room_id, started_at, is_active, source)
            VALUES (:NEW.admission_id, :NEW.room_id, v_now, 'Y', 'LIVE');
        ELSE
            -- Historical imports have no known room interval.
            INSERT INTO Admission_Room_Stay (admission_id, room_id, is_active, source)
            VALUES (:NEW.admission_id, :NEW.room_id, 'N', 'LEGACY');
        END IF;
    ELSIF :OLD.discharge_date IS NULL AND
          (:NEW.discharge_date IS NOT NULL OR :OLD.room_id <> :NEW.room_id) THEN
        UPDATE Admission_Room_Stay SET is_active = 'N', ended_at = v_now
         WHERE admission_id = :OLD.admission_id AND room_id = :OLD.room_id AND is_active = 'Y';
        IF SQL%ROWCOUNT <> 1 THEN
            RAISE_APPLICATION_ERROR(-20028, 'Room assignment history is inconsistent.');
        END IF;
        IF :NEW.discharge_date IS NULL THEN
            INSERT INTO Admission_Room_Stay (admission_id, room_id, started_at, is_active, source)
            VALUES (:NEW.admission_id, :NEW.room_id, v_now, 'Y', 'LIVE');
        END IF;
    END IF;
END;
/

-- Direct deletion of an active stay would otherwise leave its room marked Occupied.
-- Require discharge first; the application follows the same rule.
CREATE OR REPLACE TRIGGER trg_admission_delete_guard
BEFORE DELETE ON Admission
FOR EACH ROW
BEGIN
    IF :OLD.discharge_date IS NULL THEN
        RAISE_APPLICATION_ERROR(-20014, 'Discharge the patient before deleting an active admission.');
    END IF;
END;
/

PROMPT Schema objects created. Run @sql/04_verification.sql to inspect them.

-- Corrective objects shared with migration 006.
@@05_integrity_objects.sql
