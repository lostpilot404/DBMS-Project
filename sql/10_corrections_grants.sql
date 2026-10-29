-- Owner AFTER007/008 and grants07/08. No new login, secret, owner or DDL grant.
SET DEFINE ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
ACCEPT runtime_user CHAR PROMPT 'Existing restricted runtime username: '
DECLARE u VARCHAR2(128):=DBMS_ASSERT.SIMPLE_SQL_NAME(UPPER('&&runtime_user')); n NUMBER;
BEGIN
 IF u=SYS_CONTEXT('USERENV','SESSION_USER') THEN RAISE_APPLICATION_ERROR(-20210,'Runtime must not be schema owner.'); END IF;
 SELECT COUNT(*) INTO n FROM HMS_Settings WHERE correction_version=1;
 IF n<>1 THEN RAISE_APPLICATION_ERROR(-20210,'Complete008 first.'); END IF;
 FOR t IN (SELECT column_value n FROM TABLE(SYS.ODCIVARCHAR2LIST(
  'HMS_Operation','HMS_Amendment','HMS_Order_Cancel','HMS_Stock_Event','HMS_Fin_Event'))) LOOP
  EXECUTE IMMEDIATE 'GRANT SELECT,INSERT ON '||t.n||' TO '||u;
 END LOOP;
 FOR t IN (SELECT column_value n FROM TABLE(SYS.ODCIVARCHAR2LIST(
  'HMS_Stock_Opening','HMS_Legacy_Stock','V_HMS_Cash_Events','V_HMS_Batch_Recon',
  'V_HMS_Medicine_Recon','V_HMS_Care_Net','V_HMS_Return_Review'))) LOOP
  EXECUTE IMMEDIATE 'GRANT SELECT ON '||t.n||' TO '||u;
 END LOOP;
END;
/
UNDEFINE runtime_user
SET DEFINE OFF
