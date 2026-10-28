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
               OR :NEW.appointment_time <> :OLD.appointment_time THEN
                RAISE_APPLICATION_ERROR(-20020, 'Terminal appointment records are read-only history.');
            END IF;
        END IF;

        IF :OLD.status <> 'Scheduled'
           AND (:NEW.patient_id <> :OLD.patient_id
                OR :NEW.doctor_id <> :OLD.doctor_id
                OR :NEW.appointment_date <> :OLD.appointment_date
                OR :NEW.appointment_time <> :OLD.appointment_time) THEN
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

-- Admission guard: serialize room assignment with a row lock and reject unavailable rooms.
-- Unique virtual-column constraints above are a second line of defense against races.
CREATE OR REPLACE TRIGGER trg_admission_room_guard
BEFORE INSERT OR UPDATE ON Admission
FOR EACH ROW
DECLARE
    v_room_status Room.availability_status%TYPE;
BEGIN
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
