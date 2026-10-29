-- Shared read-only invariant assertions; included BEFORE008 publishes marker=1.
-- Owner only. No data changes, constraint disabling, or invented historical facts.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM HMS_Settings WHERE schema_version=6 AND multiuser_version=1 AND correction_version IN (0,1);
 IF n<>1 THEN RAISE_APPLICATION_ERROR(-20210,'Corrective schema marker missing.'); END IF;
 SELECT COUNT(*) INTO n FROM user_tables WHERE table_name IN ('HMS_OPERATION','HMS_AMENDMENT','HMS_ORDER_CANCEL','HMS_STOCK_OPENING','HMS_LEGACY_STOCK','HMS_STOCK_EVENT','HMS_FIN_EVENT');
 IF n<>7 THEN RAISE_APPLICATION_ERROR(-20210,'Corrective table inventory mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM user_objects WHERE status='INVALID';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20210,'Invalid objects; inspect USER_ERRORS.'); END IF;
 SELECT COUNT(*) INTO n FROM user_triggers WHERE status<>'ENABLED';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20210,'Disabled trigger.'); END IF;
 SELECT COUNT(*) INTO n FROM user_constraints WHERE status<>'ENABLED' OR validated<>'VALIDATED';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20210,'Unvalidated/disabled constraint.'); END IF;
 SELECT COUNT(*) INTO n FROM user_indexes WHERE status<>'VALID';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20210,'Invalid index.'); END IF;
 SELECT COUNT(*) INTO n FROM user_triggers WHERE status='ENABLED' AND trigger_name IN (
 'TRG_CC_LOCK_OPERATION','TRG_CC_KEEP_OPERATION','TRG_CC_LOCK_AMENDMENT','TRG_CC_KEEP_AMENDMENT',
 'TRG_CC_LOCK_ORDER_CANCEL','TRG_CC_KEEP_ORDER_CANCEL','TRG_CC_LOCK_STOCK_OPENING','TRG_CC_KEEP_STOCK_OPENING',
 'TRG_CC_LOCK_LEGACY_STOCK','TRG_CC_KEEP_LEGACY_STOCK','TRG_CC_LOCK_STOCK_EVENT','TRG_CC_KEEP_STOCK_EVENT',
 'TRG_CC_LOCK_FIN_EVENT','TRG_CC_KEEP_FIN_EVENT','TRG_CC_AMEND','TRG_CC_CANCEL','TRG_CC_RESULT','TRG_CC_DISPENSE',
 'TRG_CC_STOCK','TRG_CC_FIN','TRG_CC_ITEM','TRG_CC_BASE');
 IF n<>22 THEN RAISE_APPLICATION_ERROR(-20210,'Corrective trigger inventory mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM user_indexes WHERE status='VALID' AND index_name IN (
 'IX_CC_OP_USER','IX_CC_AMEND_ENC','IX_CC_AMEND_RESULT','IX_CC_AMEND_USER','IX_CC_CANCEL_USER',
 'IX_CC_STOCK_MED','IX_CC_STOCK_BATCH','IX_CC_STOCK_DISP','IX_CC_STOCK_USER','IX_CC_FIN_BILL','IX_CC_FIN_PAY',
 'IX_CC_FIN_USER','IX_CC_FIN_RELATED','IX_CC_FIN_STOCK','UQ_CC_VOID','UQ_CC_REFUND_CREDIT');
 IF n<>16 THEN RAISE_APPLICATION_ERROR(-20210,'Corrective index inventory mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM V_HMS_Batch_Recon WHERE difference<>0;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20212,'Batch journal mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM V_HMS_Medicine_Recon WHERE difference<>0;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20212,'Aggregate stock mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM V_Invoice_Balances WHERE billed<0 OR paid<0 OR balance<0 OR (void_count>0 AND (billed<>0 OR paid<>0));
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20213,'Invalid net invoice balances.'); END IF;
 SELECT COUNT(*) INTO n FROM HMS_Fin_Event r WHERE r.event_kind='REFUND' AND NOT EXISTS
 (SELECT 1 FROM HMS_Fin_Event c WHERE c.related_event_id=r.event_id AND c.event_kind='REFUND_CREDIT' AND c.amount=r.amount AND c.bill_id=r.bill_id);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20213,'Unpaired refund. Investigate without deleting original cash event.'); END IF;
 SELECT COUNT(*) INTO n FROM V_HMS_Return_Review WHERE remaining_credit<0;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20213,'Return credited more than original price.'); END IF;
END;
/
SELECT schema_version,multiuser_version,correction_version,stock_cutover_id FROM HMS_Settings;
SELECT table_name,column_name,data_type,data_precision,data_scale,identity_column FROM user_tab_cols
 WHERE table_name IN ('HMS_OPERATION','HMS_AMENDMENT','HMS_ORDER_CANCEL','HMS_STOCK_OPENING','HMS_LEGACY_STOCK','HMS_STOCK_EVENT','HMS_FIN_EVENT') ORDER BY table_name,column_id;
SELECT name,type,line,position,text FROM user_errors ORDER BY name,sequence;
SELECT * FROM V_HMS_Batch_Recon WHERE difference<>0;
SELECT * FROM V_HMS_Medicine_Recon WHERE difference<>0;
SELECT * FROM V_HMS_Return_Review ORDER BY event_id;

PROMPT Net cash by hospital month; original receipt/refund times retained, legacy basis unknown
SELECT TRUNC(CASE WHEN e.recorded_timezone='UTC' THEN
 CAST(FROM_TZ(e.recorded_at,'UTC') AT TIME ZONE s.hospital_timezone AS DATE)
 ELSE CAST(e.recorded_at AS DATE) END,'MM') cash_month,SUM(e.amount) net_collected
 FROM V_HMS_Cash_Events e CROSS JOIN HMS_Settings s
 GROUP BY TRUNC(CASE WHEN e.recorded_timezone='UTC' THEN
 CAST(FROM_TZ(e.recorded_at,'UTC') AT TIME ZONE s.hospital_timezone AS DATE)
 ELSE CAST(e.recorded_at AS DATE) END,'MM') ORDER BY cash_month;
