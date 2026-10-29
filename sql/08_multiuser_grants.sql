-- Owner only, AFTER007 and07_runtime_grants. Existing restricted login, no secrets.
SET DEFINE ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
ACCEPT runtime_user CHAR PROMPT 'Existing restricted runtime username: '
DECLARE v_user VARCHAR2(128):=DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER('&&runtime_user')); n NUMBER;
BEGIN
 IF v_user=SYS_CONTEXT('USERENV','SESSION_USER') THEN RAISE_APPLICATION_ERROR(-20200,'Runtime must not be owner.'); END IF;
 SELECT COUNT(*) INTO n FROM HMS_Settings WHERE schema_version=6 AND multiuser_version=1;
 IF n<>1 THEN RAISE_APPLICATION_ERROR(-20200,'Complete007 first.'); END IF;
 FOR t IN (SELECT column_value n FROM TABLE(SYS.ODCIVARCHAR2LIST(
 'HMS_Staff','HMS_User','HMS_Care_Assignment','HMS_Ward_Assignment','HMS_Encounter',
 'HMS_Test_Catalog','HMS_Test_Order','HMS_Appointment_Request','HMS_Medicine_Batch',
 'HMS_Care_Charge','HMS_Maintenance_Task'))) LOOP
  EXECUTE IMMEDIATE 'GRANT SELECT,INSERT,UPDATE ON '||t.n||' TO '||v_user;
 END LOOP;
 FOR t IN (SELECT column_value n FROM TABLE(SYS.ODCIVARCHAR2LIST(
 'HMS_Audit','HMS_Observation','HMS_Test_Result','HMS_Dispense'))) LOOP
  EXECUTE IMMEDIATE 'GRANT SELECT,INSERT ON '||t.n||' TO '||v_user;
 END LOOP;
 EXECUTE IMMEDIATE 'GRANT SELECT,INSERT,DELETE ON HMS_Session TO '||v_user;
 EXECUTE IMMEDIATE 'GRANT UPDATE(consultation_fee) ON HMS_Settings TO '||v_user;
 -- No account/history DELETE, no DDL, ANY privileges, roles or HMS_Internal.
END;
/
UNDEFINE runtime_user
SET DEFINE OFF
