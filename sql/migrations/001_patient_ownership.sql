-- Optional upgrade for the schema at 5db998c. Review and test on a disposable
-- copy first. DDL implicitly commits in Oracle; this script cannot be rolled
-- back as a single transaction. It neither updates nor deletes existing rows.
-- Existing incorrect associations cannot be detected or repaired automatically.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

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

-- CREATE TRIGGER can complete with compilation errors; inspect both queries.
SELECT object_name, status FROM user_objects
 WHERE object_type = 'TRIGGER' AND object_name IN ('TRG_BILL_PATIENT_GUARD', 'TRG_RX_PATIENT_GUARD');
SELECT name, line, position, text FROM user_errors
 WHERE name IN ('TRG_BILL_PATIENT_GUARD', 'TRG_RX_PATIENT_GUARD') ORDER BY name, sequence;
