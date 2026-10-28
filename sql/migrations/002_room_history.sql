-- Migration 002: room history for the schema at 5db998c.
-- NOT tested on Oracle. Rehearse on a disposable COPY first. Stop ALL writers
-- for the entire migration, including before preflight and until validation.
-- Oracle DDL implicitly commits. On failure inspect objects and restore/rehearse;
-- do not blindly rerun and do not run against a production/important schema.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE
    n NUMBER;
BEGIN
    SELECT COUNT(*) INTO n FROM user_objects WHERE object_name IN
        ('ADMISSION_ROOM_STAY','TRG_ADMISSION_STAY_SYNC');
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20101, 'Room history objects already exist; review before proceeding.'); END IF;
    SELECT COUNT(*) INTO n FROM Admission a JOIN Room r ON r.room_id = a.room_id
     WHERE a.discharge_date IS NULL AND r.availability_status <> 'Occupied';
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20102, 'Active admission/room status mismatch.'); END IF;
    SELECT COUNT(*) INTO n FROM Room r WHERE r.availability_status = 'Occupied'
      AND NOT EXISTS (SELECT 1 FROM Admission a WHERE a.room_id = r.room_id AND a.discharge_date IS NULL);
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20103, 'Occupied room has no active admission.'); END IF;
    SELECT COUNT(*) INTO n FROM (SELECT room_id FROM Admission WHERE discharge_date IS NULL GROUP BY room_id HAVING COUNT(*) > 1);
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20104, 'Duplicate active room assignments.'); END IF;
    SELECT COUNT(*) INTO n FROM (SELECT patient_id FROM Admission WHERE discharge_date IS NULL GROUP BY patient_id HAVING COUNT(*) > 1);
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20105, 'Duplicate active patient admissions.'); END IF;
END;
/
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

-- Exactly one known last-room snapshot per existing admission; no fabricated interval.
INSERT INTO Admission_Room_Stay (admission_id, room_id, is_active, source)
SELECT admission_id, room_id, CASE WHEN discharge_date IS NULL THEN 'Y' ELSE 'N' END, 'LEGACY'
  FROM Admission;
COMMIT;
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

DECLARE
    n NUMBER;
BEGIN
    SELECT COUNT(*) INTO n FROM user_objects WHERE object_type = 'TRIGGER'
      AND object_name IN ('TRG_ADMISSION_STAY_SYNC','TRG_ADMISSION_ROOM_GUARD') AND status <> 'VALID';
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20106, 'Migration trigger is invalid; inspect USER_ERRORS.'); END IF;
    SELECT COUNT(*) INTO n FROM Admission a LEFT JOIN Admission_Room_Stay s
      ON s.admission_id = a.admission_id AND s.room_id = a.room_id AND s.is_active = 'Y'
     WHERE a.discharge_date IS NULL AND s.stay_id IS NULL;
    IF n <> 0 THEN RAISE_APPLICATION_ERROR(-20107, 'Active admission missing room history.'); END IF;
END;
/
PROMPT Room history migration completed. Review USER_ERRORS and verify before reopening writers.
