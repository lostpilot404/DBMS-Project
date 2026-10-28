-- Migration 003: appointment durations. UNTESTED on Oracle. Stop all writers.
-- Rehearse on a disposable schema after migrations 001 and 002. Oracle DDL
-- commits implicitly. Preflight is not a substitute for backup or review.
-- Legacy rows receive 30 minutes as an explicit policy assumption, not a
-- recovered historical duration. Review existing appointments before applying.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE
    n NUMBER;
BEGIN
    SELECT COUNT(*) INTO n FROM user_tab_columns WHERE table_name = 'APPOINTMENT' AND column_name = 'DURATION_MINUTES';
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20110, 'Duration already exists; inspect migration state.'); END IF;
    SELECT COUNT(*) INTO n FROM Appointment
      WHERE (TO_NUMBER(SUBSTR(appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(appointment_time,4,2)) + 30) > 1440;
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20111, 'Legacy appointment extends past midnight under 30 minute policy.'); END IF;
    SELECT COUNT(*) INTO n FROM Appointment a JOIN Appointment b
      ON a.doctor_id = b.doctor_id AND a.appointment_date = b.appointment_date AND a.appointment_id < b.appointment_id
     WHERE a.status IN ('Scheduled','Checked In','Waiting','In Consultation')
       AND b.status IN ('Scheduled','Checked In','Waiting','In Consultation')
       AND (TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(a.appointment_time,4,2))) <
           (TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(b.appointment_time,4,2)) + 30)
       AND (TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(a.appointment_time,4,2)) + 30) >
           (TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(b.appointment_time,4,2)));
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20112, 'Existing active doctor appointments overlap under 30 minute policy.'); END IF;
END;
/
ALTER TABLE Appointment ADD (duration_minutes NUMBER(4) DEFAULT 30 NOT NULL);
ALTER TABLE Appointment ADD CONSTRAINT ck_appt_duration CHECK (duration_minutes BETWEEN 1 AND 1440);
ALTER TABLE Appointment ADD CONSTRAINT ck_appt_end_day CHECK
 ((TO_NUMBER(SUBSTR(appointment_time,1,2))*60 + TO_NUMBER(SUBSTR(appointment_time,4,2)) + duration_minutes) <= 1440);
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

DECLARE n NUMBER;
BEGIN
    SELECT COUNT(*) INTO n FROM user_objects WHERE object_name = 'TRG_APPOINTMENT_GUARD' AND object_type = 'TRIGGER' AND status = 'VALID';
    IF n <> 1 THEN RAISE_APPLICATION_ERROR(-20113, 'Appointment trigger invalid or missing; inspect USER_ERRORS.'); END IF;
END;
/
