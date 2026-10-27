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
UNION ALL SELECT 'MEDICINE', COUNT(*) FROM Medicine
UNION ALL SELECT 'PRESCRIPTION', COUNT(*) FROM Prescription
UNION ALL SELECT 'BILL', COUNT(*) FROM Bill
ORDER BY table_name;

PROMPT --- Columns, data types, nullability, identity / virtual metadata ---
SELECT table_name, column_id, column_name, data_type, data_length,
       data_precision, data_scale, nullable, identity_column, virtual_column
  FROM user_tab_cols
 WHERE table_name IN ('DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',
                      'ADMISSION','MEDICINE','PRESCRIPTION','BILL')
 ORDER BY table_name, column_id;

PROMPT --- Enabled primary, foreign, unique and check constraints ---
SELECT c.table_name, c.constraint_name, c.constraint_type, c.status,
       cc.column_name, c.r_constraint_name
  FROM user_constraints c
  LEFT JOIN user_cons_columns cc
    ON cc.constraint_name = c.constraint_name
   AND cc.table_name = c.table_name
 WHERE c.table_name IN ('DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',
                        'ADMISSION','MEDICINE','PRESCRIPTION','BILL')
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
                         'ADMISSION','MEDICINE','PRESCRIPTION','BILL')
 ORDER BY fk.table_name, fk.constraint_name, fkc.position;

PROMPT --- Indexes (including indexes backing uniqueness constraints) ---
SELECT table_name, index_name, uniqueness, status
  FROM user_indexes
 WHERE table_name IN ('DEPARTMENT','DOCTOR','PATIENT','APPOINTMENT','ROOM',
                      'ADMISSION','MEDICINE','PRESCRIPTION','BILL')
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
                       'TRG_APPOINTMENT_GUARD','TRG_ADMISSION_ROOM_GUARD',
                       'TRG_ADMISSION_ROOM_SYNC','TRG_ADMISSION_DELETE_GUARD')
 ORDER BY object_type, object_name;

PROMPT --- Compilation diagnostics (no rows means no reported errors) ---
SELECT name, type, line, position, text
  FROM user_errors
 WHERE name IN ('TRG_APPOINTMENT_GUARD',
                'TRG_ADMISSION_ROOM_GUARD','TRG_ADMISSION_ROOM_SYNC','TRG_ADMISSION_DELETE_GUARD',
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
SELECT 'OUTSTANDING_BILLS', COUNT(*)
  FROM Bill WHERE payment_status = 'Pending';

PROMPT Verification queries completed. Review any INVALID objects and diagnostic rows above.
