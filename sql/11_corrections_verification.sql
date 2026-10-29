-- Owner read-only readiness postflight AFTER008 (not a migration/resume script).
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
@@12_correction_invariants.sql
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM HMS_Settings WHERE schema_version=6 AND multiuser_version=1 AND correction_version=1;
 IF n<>1 THEN RAISE_APPLICATION_ERROR(-20210,'008 did not publish readiness. Keep writers stopped.'); END IF;
END;
/
PROMPT Corrective schema postflight passed. Real runtime/concurrency/upgrade evidence still required.
