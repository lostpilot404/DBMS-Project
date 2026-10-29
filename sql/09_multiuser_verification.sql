-- Read-only owner postflight; empty account tables are valid before bootstrap.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK
DECLARE n NUMBER;
BEGIN
 SELECT COUNT(*) INTO n FROM HMS_Settings WHERE schema_version=6 AND multiuser_version=1;
 IF n<>1 THEN RAISE_APPLICATION_ERROR(-20200,'007 version marker missing.'); END IF;
 SELECT COUNT(*) INTO n FROM user_tables WHERE table_name IN (
 'HMS_STAFF','HMS_USER','HMS_SESSION','HMS_AUDIT','HMS_CARE_ASSIGNMENT','HMS_WARD_ASSIGNMENT',
 'HMS_ENCOUNTER','HMS_OBSERVATION','HMS_TEST_CATALOG','HMS_TEST_ORDER','HMS_TEST_RESULT',
 'HMS_APPOINTMENT_REQUEST','HMS_MEDICINE_BATCH','HMS_DISPENSE','HMS_CARE_CHARGE','HMS_MAINTENANCE_TASK');
 IF n<>16 THEN RAISE_APPLICATION_ERROR(-20200,'Multi-user table inventory mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM user_objects WHERE status='INVALID';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20200,'Invalid objects; inspect USER_ERRORS.'); END IF;
 SELECT COUNT(*) INTO n FROM user_triggers WHERE status='ENABLED' AND trigger_name IN (
 'TRG_MU_STAFF','TRG_MU_USER','TRG_MU_SESSION','TRG_MU_AUDIT','TRG_MU_CARE_ASSIGNMENT','TRG_MU_WARD_ASSIGNMENT','TRG_MU_ENCOUNTER','TRG_MU_OBSERVATION','TRG_MU_TEST_CATALOG','TRG_MU_TEST_ORDER','TRG_MU_TEST_RESULT','TRG_MU_APPOINTMENT_REQUEST','TRG_MU_MEDICINE_BATCH','TRG_MU_DISPENSE','TRG_MU_CARE_CHARGE','TRG_MU_MAINTENANCE_TASK','TRG_MU_ACCOUNT_DELETE','TRG_MU_AUDIT_GUARD','TRG_MU_BATCH_STOCK','TRG_MU_BILL_CONTEXT','TRG_KEEP_ENCOUNTER','TRG_KEEP_OBSERVATION','TRG_KEEP_TEST_ORDER','TRG_KEEP_TEST_RESULT','TRG_KEEP_DISPENSE','TRG_KEEP_CARE_CHARGE','TRG_KEEP_APPOINTMENT_REQUEST','TRG_IMMUTABLE_OBSERVATION','TRG_IMMUTABLE_TEST_RESULT','TRG_IMMUTABLE_DISPENSE','TRG_MU_ENCOUNTER_GUARD','TRG_MU_RX_CONTEXT','TRG_MU_CHARGE_GUARD','TRG_MU_DISCHARGE_GUARD','TRG_MU_MEDICINE_GUARD');
 IF n<>35 THEN RAISE_APPLICATION_ERROR(-20200,'Missing/disabled expected007 trigger.'); END IF;
 SELECT COUNT(*) INTO n FROM user_indexes WHERE status='VALID' AND index_name IN ('UQ_FINAL_ENCOUNTER_BILL','UQ_FINAL_ADMISSION_BILL','UQ_MAINTENANCE_INPROGRESS','IX_SESSION_USER','IX_SESSION_EXPIRY');
 IF n<>5 THEN RAISE_APPLICATION_ERROR(-20200,'Missing/invalid multi-user unique/session index.'); END IF;
 SELECT COUNT(*) INTO n FROM user_triggers WHERE status<>'ENABLED';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20200,'Disabled trigger.'); END IF;
 SELECT COUNT(*) INTO n FROM user_constraints WHERE status<>'ENABLED' OR validated<>'VALIDATED';
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20200,'Disabled/unvalidated constraint.'); END IF;
 SELECT COUNT(*) INTO n FROM HMS_Encounter e JOIN Appointment a ON a.appointment_id=e.appointment_id
 WHERE e.patient_id<>a.patient_id OR e.doctor_id<>a.doctor_id;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20203,'Encounter appointment ownership mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM HMS_Encounter e JOIN Admission a ON a.admission_id=e.admission_id WHERE e.patient_id<>a.patient_id;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20203,'Encounter admission ownership mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM Prescription rx JOIN HMS_Encounter e ON e.encounter_id=rx.encounter_id
 WHERE rx.patient_id<>e.patient_id OR rx.doctor_id<>e.doctor_id OR rx.ordered_quantity IS NULL;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20203,'Prescription context/quantity mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM Prescription rx WHERE rx.ordered_quantity IS NOT NULL
 AND rx.ordered_quantity<(SELECT NVL(SUM(d.quantity),0) FROM HMS_Dispense d WHERE d.prescription_id=rx.prescription_id);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20202,'Over-dispensing.'); END IF;
 SELECT COUNT(*) INTO n FROM HMS_Dispense d JOIN Prescription rx ON rx.prescription_id=d.prescription_id
 JOIN HMS_Medicine_Batch b ON b.batch_id=d.batch_id WHERE b.medicine_id<>rx.medicine_id;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20203,'Dispensed batch medicine mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM Medicine m WHERE m.stock_quantity<
 (SELECT NVL(SUM(b.quantity),0) FROM HMS_Medicine_Batch b WHERE b.medicine_id=m.medicine_id);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20202,'Known batch balances exceed aggregate stock.'); END IF;
 SELECT COUNT(*) INTO n FROM Bill b LEFT JOIN HMS_Encounter e ON e.encounter_id=b.encounter_id
 LEFT JOIN Admission a ON a.admission_id=b.admission_id WHERE
 (b.encounter_id IS NOT NULL AND b.patient_id<>e.patient_id) OR (b.admission_id IS NOT NULL AND b.patient_id<>a.patient_id);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20203,'Invoice care ownership mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM HMS_Care_Charge c JOIN Bill_Item i ON i.item_id=c.bill_item_id
 JOIN Bill b ON b.bill_id=i.bill_id JOIN HMS_Encounter e ON e.encounter_id=c.encounter_id WHERE b.patient_id<>e.patient_id;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20203,'Charge invoice patient mismatch.'); END IF;
 SELECT COUNT(*) INTO n FROM HMS_Test_Order o LEFT JOIN HMS_Test_Result r ON r.order_id=o.order_id
 WHERE (o.status='Resulted' AND r.result_id IS NULL) OR (o.status='Ordered' AND r.result_id IS NOT NULL);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20203,'Test/result status mismatch.'); END IF;
END;
/
SELECT name,type,line,position,text FROM user_errors ORDER BY name,sequence;
PROMPT Multi-user postflight passed. Still run v6 verification and live/API/runtime/race tests.
