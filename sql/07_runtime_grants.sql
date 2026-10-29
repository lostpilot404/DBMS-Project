-- Owner-only optional setup AFTER v6 installation. Provision runtime login/quota
-- separately using your DBA workflow; do not put passwords here.
SET DEFINE ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
ACCEPT runtime_user CHAR PROMPT 'Existing restricted runtime username: '
DECLARE
 v_user VARCHAR2(128):=DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER('&&runtime_user'));
BEGIN
 IF v_user=SYS_CONTEXT('USERENV','SESSION_USER') THEN
  RAISE_APPLICATION_ERROR(-20143,'Runtime must not be the owner.');
 END IF;
 FOR t IN (SELECT column_value n FROM TABLE(SYS.ODCIVARCHAR2LIST(
   'Department','Doctor','Patient','Room','Medicine'))) LOOP
  EXECUTE IMMEDIATE 'GRANT SELECT, INSERT, UPDATE, DELETE ON '||t.n||' TO '||v_user;
 END LOOP;
 FOR t IN (SELECT column_value n FROM TABLE(SYS.ODCIVARCHAR2LIST(
   'Appointment','Admission','Prescription','Bill','Bill_Item'))) LOOP
  EXECUTE IMMEDIATE 'GRANT SELECT, INSERT, UPDATE ON '||t.n||' TO '||v_user;
 END LOOP;
 EXECUTE IMMEDIATE 'GRANT DELETE ON Bill_Item TO '||v_user;
 EXECUTE IMMEDIATE 'GRANT SELECT, INSERT ON Bill_Payment TO '||v_user;
 EXECUTE IMMEDIATE 'GRANT SELECT ON Admission_Room_Stay TO '||v_user;
 EXECUTE IMMEDIATE 'GRANT SELECT ON V_Invoice_Balances TO '||v_user;
 EXECUTE IMMEDIATE 'GRANT SELECT ON HMS_Settings TO '||v_user;
 EXECUTE IMMEDIATE 'GRANT SELECT, UPDATE ON HMS_Write_Mutex TO '||v_user;
 EXECUTE IMMEDIATE 'GRANT EXECUTE ON HMS_Today TO '||v_user;
 -- DO NOT grant HMS_Internal, DDL, ANY privileges, owner credentials or broad roles.
END;
/
UNDEFINE runtime_user
SET DEFINE OFF
