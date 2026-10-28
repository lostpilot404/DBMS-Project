-- Oracle data-dictionary checks for the nine-table project schema.
SET PAGESIZE 100
SET LINESIZE 220
SET LONG 2000
SET DEFINE OFF

PROMPT --- Actual project row counts ---
SELECT 'DEPARTMENT' AS table_name, COUNT(*) AS row_count FROM Department
UNION ALL SELECT 'DOCTOR', COUNT(*) FROM Doctor
UNION ALL SELECT 'PATIENT', COUNT(*) FROM Patient
UNION ALL SELECT 'APPOINTMENT', COUNT(*) FROM Appointment
UNION ALL SELECT 'ROOM', COUNT(*) FROM Room
UNION ALL SELECT 'ADMISSION', COUNT(*) FROM Admission
UNION ALL SELECT 'ADMISSION_ROOM_STAY', COUNT(*) FROM Admission_Room_Stay
UNION ALL SELECT 'MEDICINE', COUNT(*) FROM Medicine
UNION ALL SELECT 'PRESCRIPTION', COUNT(*) FROM Prescription
UNION ALL SELECT 'BILL_ITEM', COUNT(*) FROM Bill_Item
UNION ALL SELECT 'BILL_PAYMENT', COUNT(*) FROM Bill_Payment
UNION ALL SELECT 'BILL', COUNT(*) FROM Bill
ORDER BY table_name;

PROMPT --- Columns, data types, nullability, identity / virtual metadata ---
SELECT table_name, column_id, column_name, data_type, data_length,
       data_precision, data_scale, nullable, identity_column, virtual_column
  FROM user_tab_cols
 WHERE table_name IN ('DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',
                      'ADMISSION','MEDICINE','PRESCRIPTION','BILL','ADMISSION_ROOM_STAY','BILL_ITEM','BILL_PAYMENT')
 ORDER BY table_name, column_id;

PROMPT --- Enabled primary, foreign, unique and check constraints ---
SELECT c.table_name, c.constraint_name, c.constraint_type, c.status,
       cc.column_name, c.r_constraint_name
  FROM user_constraints c
  LEFT JOIN user_cons_columns cc
    ON cc.constraint_name = c.constraint_name
   AND cc.table_name = c.table_name
 WHERE c.table_name IN ('DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',
                        'ADMISSION','MEDICINE','PRESCRIPTION','BILL','ADMISSION_ROOM_STAY','BILL_ITEM','BILL_PAYMENT')
 ORDER BY c.table_name, c.constraint_type, c.constraint_name, cc.position;

PROMPT --- Foreign-key parent table and columns ---
SELECT fk.table_name AS child_table,
       fk.constraint_name AS foreign_key,
       fkc.column_name AS child_column,
       pk.table_name AS parent_table,
       pkc.column_name AS parent_column,
       fk.status
  FROM user_constraints fk
  JOIN user_cons_columns fkc
    ON fkc.constraint_name = fk.constraint_name
   AND fkc.table_name = fk.table_name
  JOIN user_constraints pk
    ON pk.constraint_name = fk.r_constraint_name
  JOIN user_cons_columns pkc
    ON pkc.constraint_name = pk.constraint_name
   AND pkc.position = fkc.position
 WHERE fk.constraint_type = 'R'
   AND fk.table_name IN ('DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',
                         'ADMISSION','MEDICINE','PRESCRIPTION','BILL','ADMISSION_ROOM_STAY','BILL_ITEM','BILL_PAYMENT')
 ORDER BY fk.table_name, fk.constraint_name, fkc.position;

PROMPT --- Indexes (including indexes backing uniqueness constraints) ---
SELECT table_name, index_name, uniqueness, status
  FROM user_indexes
 WHERE table_name IN ('DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',
                      'ADMISSION','MEDICINE','PRESCRIPTION','BILL','ADMISSION_ROOM_STAY','BILL_ITEM','BILL_PAYMENT')
 ORDER BY table_name, index_name;

PROMPT --- Appointment and admission triggers and compilation status ---
SELECT trigger_name, status, triggering_event, table_name
  FROM user_triggers
 WHERE table_name IN ('APPOINTMENT', 'ADMISSION')
 ORDER BY table_name, trigger_name;

PROMPT --- Appointment lifecycle status counts ---
SELECT status, COUNT(*) AS appointment_count
  FROM Appointment
 GROUP BY status
 ORDER BY status;

PROMPT --- Today's active queue counts ---
SELECT COUNT(*) AS appointments_in_today_queue
  FROM Appointment
 WHERE appointment_date = TRUNC(SYSDATE)
   AND status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation');

PROMPT --- View / trigger object status ---
SELECT object_name, object_type, status
  FROM user_objects
 WHERE object_name IN ('V_PATIENT_APPOINTMENTS','V_OUTSTANDING_BILLS',
                       'TRG_BILL_PATIENT_GUARD','TRG_RX_PATIENT_GUARD','TRG_BILL_ITEM_GUARD','TRG_BILL_CHARGE_GUARD','TRG_BILL_PAYMENT_GUARD',
                       'TRG_APPT_OVERLAP','TRG_APPOINTMENT_GUARD','TRG_ADMISSION_ROOM_GUARD',
                       'TRG_ADMISSION_ROOM_SYNC','TRG_ADMISSION_DELETE_GUARD','TRG_ADMISSION_STAY_SYNC')
 ORDER BY object_type, object_name;

PROMPT --- Compilation diagnostics (no rows means no reported errors) ---
SELECT name, type, line, position, text
  FROM user_errors
 WHERE name IN ('TRG_BILL_PATIENT_GUARD', 'TRG_RX_PATIENT_GUARD', 'TRG_BILL_ITEM_GUARD', 'TRG_BILL_CHARGE_GUARD', 'TRG_BILL_PAYMENT_GUARD', 'TRG_APPT_OVERLAP', 'TRG_APPOINTMENT_GUARD',
                'TRG_ADMISSION_ROOM_GUARD','TRG_ADMISSION_ROOM_SYNC','TRG_ADMISSION_DELETE_GUARD','TRG_ADMISSION_STAY_SYNC',
                'V_PATIENT_APPOINTMENTS','V_OUTSTANDING_BILLS')
 ORDER BY name, sequence;

PROMPT --- Relationship sanity counts ---
SELECT 'DOCTOR_WITHOUT_DEPARTMENT' AS check_name, COUNT(*) AS issue_count
  FROM Doctor d LEFT JOIN Department dep ON dep.department_id = d.department_id
 WHERE dep.department_id IS NULL
UNION ALL
SELECT 'ACTIVE_ADMISSIONS', COUNT(*)
  FROM Admission WHERE discharge_date IS NULL
UNION ALL
SELECT 'ACTIVE_ROOM_STATUS_MISMATCH', COUNT(*)
  FROM Admission a JOIN Room r ON r.room_id = a.room_id
 WHERE a.discharge_date IS NULL AND r.availability_status <> 'Occupied'
UNION ALL
SELECT 'ACTIVE_HISTORY_MISMATCH', COUNT(*)
  FROM Admission a LEFT JOIN Admission_Room_Stay s
    ON s.admission_id = a.admission_id AND s.room_id = a.room_id AND s.is_active = 'Y'
 WHERE a.discharge_date IS NULL AND s.stay_id IS NULL
UNION ALL
SELECT 'ORPHAN_ACTIVE_STAYS', COUNT(*)
  FROM Admission_Room_Stay s JOIN Admission a ON a.admission_id = s.admission_id
 WHERE s.is_active = 'Y' AND (a.discharge_date IS NOT NULL OR a.room_id <> s.room_id)
UNION ALL
SELECT 'OCCUPIED_WITHOUT_STAY', COUNT(*)
  FROM Room r WHERE r.availability_status = 'Occupied'
   AND NOT EXISTS (SELECT 1 FROM Admission_Room_Stay s WHERE s.room_id = r.room_id AND s.is_active = 'Y')
UNION ALL
SELECT 'DUPLICATE_ACTIVE_ROOMS', COUNT(*) FROM
 (SELECT room_id FROM Admission_Room_Stay WHERE is_active = 'Y' GROUP BY room_id HAVING COUNT(*) > 1)
UNION ALL
SELECT 'DUPLICATE_ACTIVE_ADMISSIONS', COUNT(*) FROM
 (SELECT admission_id FROM Admission_Room_Stay WHERE is_active = 'Y' GROUP BY admission_id HAVING COUNT(*) > 1)
UNION ALL
SELECT 'DISCHARGED_WITH_OPEN_STAY', COUNT(*)
  FROM Admission_Room_Stay s JOIN Admission a ON a.admission_id = s.admission_id
 WHERE s.is_active = 'Y' AND a.discharge_date IS NOT NULL
UNION ALL
SELECT 'LEDGER_OVERPAYMENTS', COUNT(*) FROM Bill b
 WHERE NVL((SELECT SUM(p.amount) FROM Bill_Payment p WHERE p.bill_id = b.bill_id), 0)
       > b.total_amount + NVL((SELECT SUM(i.line_total) FROM Bill_Item i WHERE i.bill_id = b.bill_id), 0)
UNION ALL
SELECT 'OUTSTANDING_BILLS', COUNT(*)
  FROM Bill WHERE payment_status = 'Pending';

PROMPT Verification queries completed. Review any INVALID objects and diagnostic rows above.
