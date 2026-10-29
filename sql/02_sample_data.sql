-- Fictional, repeat-safe demonstration data. No DROP or DELETE statements.
-- Date expressions are relative to HMS_Today() so upcoming appointments stay useful.
SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

-- Departments
INSERT INTO Department (department_name, location)
SELECT 'Cardiology', 'Block A - Level 2' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Department WHERE department_name = 'Cardiology');
INSERT INTO Department (department_name, location)
SELECT 'Paediatrics', 'Block B - Level 1' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Department WHERE department_name = 'Paediatrics');
INSERT INTO Department (department_name, location)
SELECT 'Orthopaedics', 'Block A - Level 3' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Department WHERE department_name = 'Orthopaedics');
INSERT INTO Department (department_name, location)
SELECT 'General Medicine', 'Block C - Level 1' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Department WHERE department_name = 'General Medicine');

-- Doctors
INSERT INTO Doctor (doctor_name, specialization, phone, email, department_id)
SELECT 'Dr. Meera Raman', 'Cardiology', '+91-90000-10001', 'meera.raman@example.test', d.department_id
  FROM Department d
 WHERE d.department_name = 'Cardiology'
   AND NOT EXISTS (SELECT 1 FROM Doctor x WHERE x.email = 'meera.raman@example.test');
INSERT INTO Doctor (doctor_name, specialization, phone, email, department_id)
SELECT 'Dr. Arjun Nair', 'Interventional Cardiology', '+91-90000-10002', 'arjun.nair@example.test', d.department_id
  FROM Department d
 WHERE d.department_name = 'Cardiology'
   AND NOT EXISTS (SELECT 1 FROM Doctor x WHERE x.email = 'arjun.nair@example.test');
INSERT INTO Doctor (doctor_name, specialization, phone, email, department_id)
SELECT 'Dr. Kavya Iyer', 'Paediatrics', '+91-90000-10003', 'kavya.iyer@example.test', d.department_id
  FROM Department d
 WHERE d.department_name = 'Paediatrics'
   AND NOT EXISTS (SELECT 1 FROM Doctor x WHERE x.email = 'kavya.iyer@example.test');
INSERT INTO Doctor (doctor_name, specialization, phone, email, department_id)
SELECT 'Dr. Rohan Das', 'Orthopaedics', '+91-90000-10004', 'rohan.das@example.test', d.department_id
  FROM Department d
 WHERE d.department_name = 'Orthopaedics'
   AND NOT EXISTS (SELECT 1 FROM Doctor x WHERE x.email = 'rohan.das@example.test');
INSERT INTO Doctor (doctor_name, specialization, phone, email, department_id)
SELECT 'Dr. Sana Joseph', 'General Medicine', '+91-90000-10005', 'sana.joseph@example.test', d.department_id
  FROM Department d
 WHERE d.department_name = 'General Medicine'
   AND NOT EXISTS (SELECT 1 FROM Doctor x WHERE x.email = 'sana.joseph@example.test');

-- Patients (all names, addresses, phones and emails are fictional).
INSERT INTO Patient (patient_name, date_of_birth, gender, phone, address, blood_group)
SELECT 'Aarav Menon', DATE '1987-04-18', 'M', '+91-90001-20001', '12 Lake View Road, Vellore', 'O+'
  FROM dual WHERE NOT EXISTS (SELECT 1 FROM Patient WHERE phone = '+91-90001-20001');
INSERT INTO Patient (patient_name, date_of_birth, gender, phone, address, blood_group)
SELECT 'Diya Krishnan', DATE '1994-11-02', 'F', '+91-90001-20002', '8 Temple Street, Katpadi', 'A+'
  FROM dual WHERE NOT EXISTS (SELECT 1 FROM Patient WHERE phone = '+91-90001-20002');
INSERT INTO Patient (patient_name, date_of_birth, gender, phone, address, blood_group)
SELECT 'Kabir Shah', DATE '1973-07-29', 'M', '+91-90001-20003', '41 Market Road, Vellore', 'B+'
  FROM dual WHERE NOT EXISTS (SELECT 1 FROM Patient WHERE phone = '+91-90001-20003');
INSERT INTO Patient (patient_name, date_of_birth, gender, phone, address, blood_group)
SELECT 'Ananya Rao', DATE '2002-01-15', 'F', '+91-90001-20004', '5 Green Park, Vellore', 'AB+'
  FROM dual WHERE NOT EXISTS (SELECT 1 FROM Patient WHERE phone = '+91-90001-20004');
INSERT INTO Patient (patient_name, date_of_birth, gender, phone, address, blood_group)
SELECT 'Ishaan Kumar', DATE '2016-09-23', 'M', '+91-90001-20005', '19 New Town, Katpadi', 'O-'
  FROM dual WHERE NOT EXISTS (SELECT 1 FROM Patient WHERE phone = '+91-90001-20005');
INSERT INTO Patient (patient_name, date_of_birth, gender, phone, address, blood_group)
SELECT 'Nila Thomas', DATE '1968-12-06', 'F', '+91-90001-20006', '2 River Bank, Vellore', 'B-'
  FROM dual WHERE NOT EXISTS (SELECT 1 FROM Patient WHERE phone = '+91-90001-20006');
INSERT INTO Patient (patient_name, date_of_birth, gender, phone, address, blood_group)
SELECT 'Vikram Patel', DATE '1981-05-31', 'M', '+91-90001-20007', '27 Gandhi Road, Katpadi', 'A-'
  FROM dual WHERE NOT EXISTS (SELECT 1 FROM Patient WHERE phone = '+91-90001-20007');
INSERT INTO Patient (patient_name, date_of_birth, gender, phone, address, blood_group)
SELECT 'Tara Suresh', DATE '1999-08-12', 'O', '+91-90001-20008', '10 Hill Street, Vellore', 'AB-'
  FROM dual WHERE NOT EXISTS (SELECT 1 FROM Patient WHERE phone = '+91-90001-20008');

-- Rooms
INSERT INTO Room (room_number, room_type, availability_status)
SELECT 'R-101', 'Private', 'Available' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Room WHERE room_number = 'R-101');
INSERT INTO Room (room_number, room_type, availability_status)
SELECT 'R-102', 'Semi-private', 'Available' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Room WHERE room_number = 'R-102');
INSERT INTO Room (room_number, room_type, availability_status)
SELECT 'R-103', 'General', 'Available' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Room WHERE room_number = 'R-103');
INSERT INTO Room (room_number, room_type, availability_status)
SELECT 'R-104', 'Private', 'Available' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Room WHERE room_number = 'R-104');
INSERT INTO Room (room_number, room_type, availability_status)
SELECT 'R-105', 'ICU', 'Maintenance' FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Room WHERE room_number = 'R-105');

-- Medicines
INSERT INTO Medicine (medicine_name, manufacturer, price, stock_quantity)
SELECT 'Paracetamol 500 mg', 'Crescent Pharma', 2.50, 240 FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Medicine WHERE medicine_name = 'Paracetamol 500 mg');
INSERT INTO Medicine (medicine_name, manufacturer, price, stock_quantity)
SELECT 'Amoxicillin 250 mg', 'Riverbend Labs', 8.75, 120 FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Medicine WHERE medicine_name = 'Amoxicillin 250 mg');
INSERT INTO Medicine (medicine_name, manufacturer, price, stock_quantity)
SELECT 'Amlodipine 5 mg', 'Northstar Remedies', 6.25, 6 FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Medicine WHERE medicine_name = 'Amlodipine 5 mg');
INSERT INTO Medicine (medicine_name, manufacturer, price, stock_quantity)
SELECT 'ORS Sachet', 'Crescent Pharma', 18.00, 85 FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Medicine WHERE medicine_name = 'ORS Sachet');
INSERT INTO Medicine (medicine_name, manufacturer, price, stock_quantity)
SELECT 'Vitamin D3 1000 IU', 'Hillview Healthcare', 4.00, 0 FROM dual
 WHERE NOT EXISTS (SELECT 1 FROM Medicine WHERE medicine_name = 'Vitamin D3 1000 IU');

-- Appointments: two upcoming visits, one completed through the valid lifecycle,
-- and one cancelled example. Active-slot checks include every in-progress status.
INSERT INTO Appointment (patient_id, doctor_id, appointment_date, appointment_time, status)
SELECT p.patient_id, d.doctor_id, HMS_Today() + 1, '09:00', 'Scheduled'
  FROM Patient p CROSS JOIN Doctor d
 WHERE p.phone = '+91-90001-20001' AND d.email = 'meera.raman@example.test'
   AND NOT EXISTS (SELECT 1 FROM Appointment a
                    WHERE a.doctor_id = d.doctor_id
                      AND a.appointment_date = HMS_Today() + 1
                      AND a.appointment_time = '09:00'
                      AND a.status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation'))
   AND NOT EXISTS (SELECT 1 FROM Appointment a
                    WHERE a.patient_id = p.patient_id
                      AND a.appointment_date = HMS_Today() + 1
                      AND a.appointment_time = '09:00');
INSERT INTO Appointment (patient_id, doctor_id, appointment_date, appointment_time, status)
SELECT p.patient_id, d.doctor_id, HMS_Today() + 2, '10:30', 'Scheduled'
  FROM Patient p CROSS JOIN Doctor d
 WHERE p.phone = '+91-90001-20002' AND d.email = 'kavya.iyer@example.test'
   AND NOT EXISTS (SELECT 1 FROM Appointment a
                    WHERE a.doctor_id = d.doctor_id
                      AND a.appointment_date = HMS_Today() + 2
                      AND a.appointment_time = '10:30'
                      AND a.status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation'))
   AND NOT EXISTS (SELECT 1 FROM Appointment a
                    WHERE a.patient_id = p.patient_id
                      AND a.appointment_date = HMS_Today() + 2
                      AND a.appointment_time = '10:30');

-- Seed a completed history through the valid lifecycle. The block first checks
-- for an existing patient slot, then updates only the identity it just inserted.
-- A rerun or a user-created matching appointment is left untouched.
DECLARE
    v_patient_id Patient.patient_id%TYPE;
    v_doctor_id Doctor.doctor_id%TYPE;
    v_appointment_id Appointment.appointment_id%TYPE;
BEGIN
    SELECT p.patient_id, d.doctor_id
      INTO v_patient_id, v_doctor_id
      FROM Patient p CROSS JOIN Doctor d
     WHERE p.phone = '+91-90001-20003'
       AND d.email = 'arjun.nair@example.test'
       AND NOT EXISTS (SELECT 1 FROM Appointment a
                        WHERE a.patient_id = p.patient_id
                          AND a.appointment_date = HMS_Today()
                          AND a.appointment_time = '11:00')
       AND NOT EXISTS (SELECT 1 FROM Appointment a
                        WHERE a.doctor_id = d.doctor_id
                          AND a.appointment_date = HMS_Today()
                          AND a.appointment_time = '11:00'
                          AND a.status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation'));

    INSERT INTO Appointment (patient_id, doctor_id, appointment_date, appointment_time, status)
    VALUES (v_patient_id, v_doctor_id, HMS_Today(), '11:00', 'Scheduled')
    RETURNING appointment_id INTO v_appointment_id;
    UPDATE Appointment SET status = 'Checked In' WHERE appointment_id = v_appointment_id;
    UPDATE Appointment SET status = 'Waiting' WHERE appointment_id = v_appointment_id;
    UPDATE Appointment SET status = 'In Consultation' WHERE appointment_id = v_appointment_id;
    UPDATE Appointment SET status = 'Completed' WHERE appointment_id = v_appointment_id;
EXCEPTION
    WHEN NO_DATA_FOUND THEN NULL;
END;
/

-- Seed a cancelled history through a valid Scheduled -> Cancelled transition;
-- only the newly inserted row is updated, never a pre-existing appointment.
DECLARE
    v_patient_id Patient.patient_id%TYPE;
    v_doctor_id Doctor.doctor_id%TYPE;
    v_appointment_id Appointment.appointment_id%TYPE;
BEGIN
    SELECT p.patient_id, d.doctor_id
      INTO v_patient_id, v_doctor_id
      FROM Patient p CROSS JOIN Doctor d
     WHERE p.phone = '+91-90001-20004'
       AND d.email = 'rohan.das@example.test'
       AND NOT EXISTS (SELECT 1 FROM Appointment a
                        WHERE a.patient_id = p.patient_id
                          AND a.appointment_date = HMS_Today() + 4
                          AND a.appointment_time = '14:00')
       AND NOT EXISTS (SELECT 1 FROM Appointment a
                        WHERE a.doctor_id = d.doctor_id
                          AND a.appointment_date = HMS_Today() + 4
                          AND a.appointment_time = '14:00'
                          AND a.status IN ('Scheduled', 'Checked In', 'Waiting', 'In Consultation'));

    INSERT INTO Appointment (patient_id, doctor_id, appointment_date, appointment_time, status)
    VALUES (v_patient_id, v_doctor_id, HMS_Today() + 4, '14:00', 'Scheduled')
    RETURNING appointment_id INTO v_appointment_id;
    UPDATE Appointment SET status = 'Cancelled' WHERE appointment_id = v_appointment_id;
EXCEPTION
    WHEN NO_DATA_FOUND THEN NULL;
END;
/

-- One active admission (R-101 becomes Occupied through the trigger) and one past stay.
INSERT INTO Admission (patient_id, room_id, admission_date)
SELECT p.patient_id, r.room_id, HMS_Today() - 1
  FROM Patient p CROSS JOIN Room r
 WHERE p.phone = '+91-90001-20005' AND r.room_number = 'R-101'
   AND r.availability_status = 'Available'
   AND NOT EXISTS (SELECT 1 FROM Admission a
                    WHERE a.patient_id = p.patient_id AND a.discharge_date IS NULL)
   AND NOT EXISTS (SELECT 1 FROM Admission a
                    WHERE a.room_id = r.room_id AND a.discharge_date IS NULL);
-- Historical demo: create an active admission then discharge in the same
-- transaction. Skip if the room/patient is currently in use or row exists.
DECLARE
    v_patient Patient.patient_id%TYPE;
    v_room Room.room_id%TYPE;
    v_admission Admission.admission_id%TYPE;
BEGIN
    SELECT p.patient_id, r.room_id INTO v_patient, v_room
      FROM Patient p CROSS JOIN Room r
     WHERE p.phone = '+91-90001-20006' AND r.room_number = 'R-102'
       AND r.availability_status = 'Available'
       AND NOT EXISTS (SELECT 1 FROM Admission a WHERE a.patient_id = p.patient_id
                        AND (a.discharge_date IS NULL OR
                             (a.admission_date = HMS_Today() - 10 AND a.room_id = r.room_id)))
       AND NOT EXISTS (SELECT 1 FROM Admission a WHERE a.room_id = r.room_id AND a.discharge_date IS NULL);
    INSERT INTO Admission (patient_id, room_id, admission_date)
    VALUES (v_patient, v_room, HMS_Today() - 10) RETURNING admission_id INTO v_admission;
    UPDATE Admission SET discharge_date = HMS_Today() - 7 WHERE admission_id = v_admission;
EXCEPTION WHEN NO_DATA_FOUND THEN NULL;
END;
/

-- Prescription records are clinical instructions only; creating one does not dispense stock.
INSERT INTO Prescription (patient_id, doctor_id, medicine_id, dosage, duration, prescription_date)
SELECT p.patient_id, d.doctor_id, m.medicine_id, '1 tablet after meals', '5 days', HMS_Today()
  FROM Patient p CROSS JOIN Doctor d CROSS JOIN Medicine m
 WHERE p.phone = '+91-90001-20001' AND d.email = 'meera.raman@example.test'
   AND m.medicine_name = 'Amlodipine 5 mg'
   AND NOT EXISTS (SELECT 1 FROM Prescription x
                    WHERE x.patient_id = p.patient_id AND x.medicine_id = m.medicine_id
                      AND x.prescription_date = HMS_Today());
INSERT INTO Prescription (patient_id, doctor_id, medicine_id, dosage, duration, prescription_date)
SELECT p.patient_id, d.doctor_id, m.medicine_id, '1 tablet every 6 hours as needed', '3 days', HMS_Today()
  FROM Patient p CROSS JOIN Doctor d CROSS JOIN Medicine m
 WHERE p.phone = '+91-90001-20003' AND d.email = 'sana.joseph@example.test'
   AND m.medicine_name = 'Paracetamol 500 mg'
   AND NOT EXISTS (SELECT 1 FROM Prescription x
                    WHERE x.patient_id = p.patient_id AND x.medicine_id = m.medicine_id
                      AND x.prescription_date = HMS_Today());
INSERT INTO Prescription (patient_id, doctor_id, medicine_id, dosage, duration, prescription_date)
SELECT p.patient_id, d.doctor_id, m.medicine_id, '5 ml twice daily', '7 days', HMS_Today()
  FROM Patient p CROSS JOIN Doctor d CROSS JOIN Medicine m
 WHERE p.phone = '+91-90001-20005' AND d.email = 'kavya.iyer@example.test'
   AND m.medicine_name = 'Amoxicillin 250 mg'
   AND NOT EXISTS (SELECT 1 FROM Prescription x
                    WHERE x.patient_id = p.patient_id AND x.medicine_id = m.medicine_id
                      AND x.prescription_date = HMS_Today());

-- Bills (total_amount is generated by Oracle from its component charges).
INSERT INTO Bill (patient_id, bill_date, consultation_charge, room_charge, medicine_charge, payment_status)
SELECT p.patient_id, HMS_Today() - 1, 500, 0, 125, 'Paid'
  FROM Patient p WHERE p.phone = '+91-90001-20001'
   AND NOT EXISTS (SELECT 1 FROM Bill b WHERE b.patient_id = p.patient_id
                    AND b.bill_date = HMS_Today() - 1 AND b.consultation_charge = 500);
INSERT INTO Bill (patient_id, bill_date, consultation_charge, room_charge, medicine_charge, payment_status)
SELECT p.patient_id, HMS_Today(), 400, 0, 18, 'Pending'
  FROM Patient p WHERE p.phone = '+91-90001-20002'
   AND NOT EXISTS (SELECT 1 FROM Bill b WHERE b.patient_id = p.patient_id
                    AND b.bill_date = HMS_Today() AND b.consultation_charge = 400);
INSERT INTO Bill (patient_id, bill_date, consultation_charge, room_charge, medicine_charge, payment_status)
SELECT p.patient_id, HMS_Today() - 2, 650, 1800, 44, 'Pending'
  FROM Patient p WHERE p.phone = '+91-90001-20005'
   AND NOT EXISTS (SELECT 1 FROM Bill b WHERE b.patient_id = p.patient_id
                    AND b.bill_date = HMS_Today() - 2 AND b.consultation_charge = 650);
INSERT INTO Bill (patient_id, bill_date, consultation_charge, room_charge, medicine_charge, payment_status)
SELECT p.patient_id, HMS_Today() - 4, 350, 0, 12.50, 'Paid'
  FROM Patient p WHERE p.phone = '+91-90001-20003'
   AND NOT EXISTS (SELECT 1 FROM Bill b WHERE b.patient_id = p.patient_id
                    AND b.bill_date = HMS_Today() - 4 AND b.consultation_charge = 350);
INSERT INTO Bill (patient_id, bill_date, consultation_charge, room_charge, medicine_charge, payment_status)
SELECT p.patient_id, HMS_Today(), 300, 0, 0, 'Pending'
  FROM Patient p WHERE p.phone = '+91-90001-20007'
   AND NOT EXISTS (SELECT 1 FROM Bill b WHERE b.patient_id = p.patient_id
                    AND b.bill_date = HMS_Today() AND b.consultation_charge = 300);

COMMIT;
PROMPT Fictional demo data inserted (or already present for this run date).
