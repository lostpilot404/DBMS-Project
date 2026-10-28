-- Report views and useful Oracle SQL examples.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

CREATE OR REPLACE VIEW V_PATIENT_APPOINTMENTS AS
SELECT a.appointment_id,
       a.patient_id,
       p.patient_name,
       a.doctor_id,
       d.doctor_name,
       dep.department_name,
       a.appointment_date,
       a.appointment_time,
       a.status
  FROM Appointment a
  JOIN Patient p ON p.patient_id = a.patient_id
  JOIN Doctor d ON d.doctor_id = a.doctor_id
  JOIN Department dep ON dep.department_id = d.department_id;

CREATE OR REPLACE VIEW V_OUTSTANDING_BILLS AS
SELECT b.bill_id,
       b.patient_id,
       p.patient_name,
       b.bill_date,
       b.total_amount,
       b.payment_status
  FROM Bill b
  JOIN Patient p ON p.patient_id = b.patient_id
 WHERE b.payment_status = 'Pending';

PROMPT --- All departments ---
SELECT department_id, department_name, location
  FROM Department
 ORDER BY department_name;

PROMPT --- Doctors with their departments ---
SELECT d.doctor_id, d.doctor_name, d.specialization, d.phone, d.email,
       dep.department_name
  FROM Doctor d
  JOIN Department dep ON dep.department_id = d.department_id
 ORDER BY dep.department_name, d.doctor_name;

PROMPT --- Patient appointments (joined report) ---
SELECT patient_name, doctor_name, department_name,
       appointment_date, appointment_time, status
  FROM V_PATIENT_APPOINTMENTS
 ORDER BY appointment_date DESC, appointment_time;

PROMPT --- Doctor schedule (active visits from today onwards) ---
SELECT doctor_name, patient_name, appointment_date, appointment_time, status
  FROM V_PATIENT_APPOINTMENTS
 WHERE appointment_date >= TRUNC(SYSDATE)
   AND status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation')
 ORDER BY doctor_name, appointment_date, appointment_time;

-- Queue order uses status then booked time; the model has no arrival or triage-priority field.
PROMPT --- Today's appointment queue (waiting, checked-in, then scheduled) ---
SELECT appointment_id, patient_name, doctor_name, department_name,
       appointment_date, appointment_time, status
  FROM V_PATIENT_APPOINTMENTS
 WHERE appointment_date = TRUNC(SYSDATE)
 ORDER BY CASE status
              WHEN 'Waiting' THEN 1 WHEN 'Checked In' THEN 2 WHEN 'Scheduled' THEN 3
              WHEN 'In Consultation' THEN 4 WHEN 'Completed' THEN 5
              WHEN 'No-show' THEN 6 WHEN 'Cancelled' THEN 7 ELSE 8
          END,
          appointment_time, appointment_id;

PROMPT --- Appointment counts by date and status ---
SELECT TRUNC(appointment_date) AS appointment_day, status, COUNT(*) AS appointment_count
  FROM Appointment
 GROUP BY TRUNC(appointment_date), status
 ORDER BY appointment_day DESC, status;

PROMPT --- Department-wise doctor counts (GROUP BY / HAVING) ---
SELECT dep.department_name, COUNT(d.doctor_id) AS doctor_count
  FROM Department dep
  LEFT JOIN Doctor d ON d.department_id = dep.department_id
 GROUP BY dep.department_name
HAVING COUNT(d.doctor_id) >= 1
 ORDER BY doctor_count DESC, dep.department_name;

PROMPT --- Admissions and rooms ---
SELECT a.admission_id, p.patient_name, r.room_number, r.room_type,
       r.availability_status, a.admission_date, a.discharge_date
  FROM Admission a
  JOIN Patient p ON p.patient_id = a.patient_id
  JOIN Room r ON r.room_id = a.room_id
 ORDER BY a.admission_date DESC;

PROMPT --- Current admissions only ---
SELECT a.admission_id, p.patient_id, p.patient_name, r.room_number, r.room_type, a.admission_date
  FROM Admission a
  JOIN Patient p ON p.patient_id = a.patient_id
  JOIN Room r ON r.room_id = a.room_id
 WHERE a.discharge_date IS NULL
 ORDER BY a.admission_date DESC, r.room_number;

PROMPT --- Admission and discharge history ---
SELECT a.admission_id, p.patient_name, r.room_number, a.admission_date, a.discharge_date
  FROM Admission a
  JOIN Patient p ON p.patient_id = a.patient_id
  JOIN Room r ON r.room_id = a.room_id
 ORDER BY a.admission_date DESC, a.admission_id DESC;

PROMPT --- Room assignment observations (legacy times may be unknown) ---
SELECT s.stay_id, a.admission_id, p.patient_name, r.room_number,
       s.started_at, s.ended_at, s.is_active, s.source
  FROM Admission_Room_Stay s JOIN Admission a ON a.admission_id = s.admission_id
  JOIN Patient p ON p.patient_id = a.patient_id JOIN Room r ON r.room_id = s.room_id
 ORDER BY s.stay_id;

PROMPT --- Room availability ---
SELECT room_number, room_type, availability_status
  FROM Room
 ORDER BY availability_status, room_number;

PROMPT --- Room occupancy counts ---
SELECT availability_status, COUNT(*) AS room_count
  FROM Room
 GROUP BY availability_status
 ORDER BY availability_status;

PROMPT --- Prescription history ---
SELECT p.patient_name, d.doctor_name, m.medicine_name,
       rx.dosage, rx.duration, rx.prescription_date
  FROM Prescription rx
  JOIN Patient p ON p.patient_id = rx.patient_id
  JOIN Doctor d ON d.doctor_id = rx.doctor_id
  JOIN Medicine m ON m.medicine_id = rx.medicine_id
 ORDER BY rx.prescription_date DESC, p.patient_name;

PROMPT --- Low / out-of-stock medicines ---
SELECT medicine_name, manufacturer, price, stock_quantity
  FROM Medicine
 WHERE stock_quantity < 10
 ORDER BY stock_quantity, medicine_name;

PROMPT --- Individual patient bills (change the patient ID as needed) ---
SELECT b.bill_id, p.patient_id, p.patient_name, b.bill_date,
       b.consultation_charge, b.room_charge, b.medicine_charge,
       b.total_amount, b.payment_status
  FROM Bill b JOIN Patient p ON p.patient_id = b.patient_id
 ORDER BY p.patient_name, b.bill_date DESC, b.bill_id DESC;

PROMPT --- Outstanding bill detail and balance ---
SELECT bill_id, patient_id, patient_name, bill_date, total_amount
  FROM V_OUTSTANDING_BILLS
 ORDER BY bill_date, bill_id;

PROMPT --- Paid bills and collected amount ---
SELECT b.bill_id, p.patient_id, p.patient_name, b.bill_date, b.total_amount
  FROM Bill b JOIN Patient p ON p.patient_id = b.patient_id
 WHERE b.payment_status = 'Paid'
 ORDER BY b.bill_date DESC, b.bill_id DESC;


PROMPT --- Total outstanding balance ---
SELECT NVL(SUM(total_amount), 0) AS outstanding_balance
  FROM V_OUTSTANDING_BILLS;

PROMPT --- Revenue by payment status ---
SELECT payment_status, COUNT(*) AS bill_count, SUM(total_amount) AS amount
  FROM Bill
 GROUP BY payment_status
 ORDER BY payment_status;

PROMPT --- Revenue grouped by month ---
SELECT TRUNC(bill_date, 'MM') AS revenue_month,
       SUM(CASE WHEN payment_status = 'Paid' THEN total_amount ELSE 0 END) AS paid_revenue,
       SUM(CASE WHEN payment_status = 'Pending' THEN total_amount ELSE 0 END) AS pending_amount
  FROM Bill
 GROUP BY TRUNC(bill_date, 'MM')
 ORDER BY revenue_month;

PROMPT --- Patients with at least one appointment (subquery) ---
SELECT patient_id, patient_name, phone
  FROM Patient p
 WHERE EXISTS (SELECT 1 FROM Appointment a WHERE a.patient_id = p.patient_id)
 ORDER BY patient_name;

PROMPT --- UPDATE examples (review keys and values before deliberately running) ---
-- UPDATE Doctor SET phone = '+91-90000-19999' WHERE doctor_id = :doctor_id;
-- UPDATE Appointment SET status = 'Cancelled' WHERE appointment_id = :appointment_id;
-- UPDATE Bill SET payment_status = 'Paid' WHERE bill_id = :bill_id AND payment_status = 'Pending';

PROMPT --- DELETE example (review key before deliberately running) ---
-- DELETE FROM Department WHERE department_id = :department_id;
-- The application retains appointment, admission, prescription, and billing history.
-- Do not delete a patient, doctor, medicine, room or department with dependent records.
