-- STOP ALL WRITERS, back up, rehearse on disposable clone. Owner only, Oracle12c+.
-- Requires completed 001-005. DDL autocommits. On ANY failure leave app stopped;
-- inspect USER_ERRORS and restore backup/rehearse a reviewed recovery, DO NOT rerun.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM user_tables WHERE table_name IN ('HMS_SETTINGS','HMS_WRITE_MUTEX');
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20142,'006 already/partially installed; stop and inspect.'); END IF;
 SELECT COUNT(*) INTO n FROM user_tables WHERE table_name IN ('DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM','ADMISSION','ADMISSION_ROOM_STAY','MEDICINE','PRESCRIPTION','BILL','BILL_ITEM','BILL_PAYMENT');
 IF n<>12 THEN RAISE_APPLICATION_ERROR(-20142,'Requires all twelve tables after 001-005.'); END IF;
 SELECT COUNT(*) INTO n FROM user_tab_cols WHERE table_name='APPOINTMENT' AND column_name='DURATION_MINUTES';
 IF n<>1 THEN RAISE_APPLICATION_ERROR(-20142,'Duration migration is missing.'); END IF;
 SELECT COUNT(*) INTO n FROM user_triggers WHERE status='DISABLED';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20142,'Disabled triggers; repair baseline first.'); END IF;
 SELECT COUNT(*) INTO n FROM user_constraints WHERE status<>'ENABLED' OR validated<>'VALIDATED';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20142,'Unvalidated or disabled constraints.'); END IF;
 SELECT COUNT(*) INTO n FROM user_objects WHERE status='INVALID';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20142,'Invalid baseline objects; inspect USER_ERRORS.'); END IF;
END;
/
@@../06_invariant_checks.sql
@@../05_integrity_objects.sql
@@../04_verification.sql
PROMPT Migration 006 complete. Only resume writers after successful verification.
