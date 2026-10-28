-- Migration 004: database appointment overlap guard, Oracle 12c+.
-- UNTESTED. Stop all writers; rehearse and back up a disposable schema.
-- DDL implicitly commits. Do not blindly rerun after any failure.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE
    n NUMBER;
BEGIN
    SELECT COUNT(*) INTO n FROM user_objects
     WHERE object_name IN ('TRG_APPT_OVERLAP', 'IX_APPT_DOCTOR_DAY');
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20120, 'Overlap objects already exist; inspect migration state.'); END IF;
    SELECT COUNT(*) INTO n FROM Appointment a JOIN Appointment b
      ON b.doctor_id = a.doctor_id AND b.appointment_date = a.appointment_date AND b.appointment_id > a.appointment_id
     WHERE a.status IN ('Scheduled','Checked In','Waiting','In Consultation')
       AND b.status IN ('Scheduled','Checked In','Waiting','In Consultation')
       AND (TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(a.appointment_time,4,2))) <
           (TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(b.appointment_time,4,2))+b.duration_minutes)
       AND (TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(a.appointment_time,4,2))+a.duration_minutes) >
           (TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(b.appointment_time,4,2)));
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20121, 'Existing active doctor intervals overlap; resolve before migration.'); END IF;
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
DECLARE n NUMBER;
BEGIN
    SELECT COUNT(*) INTO n FROM user_objects WHERE object_name = 'TRG_APPT_OVERLAP'
      AND object_type = 'TRIGGER' AND status = 'VALID';
    IF n <> 1 THEN RAISE_APPLICATION_ERROR(-20122, 'Overlap trigger missing or invalid; inspect USER_ERRORS.'); END IF;
END;
/
