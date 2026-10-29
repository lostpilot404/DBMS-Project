-- Executable fail-fast invariants shared by migration preflight and verification.
DECLARE n NUMBER; v_today DATE;
BEGIN
 SELECT COUNT(*) INTO n FROM user_objects WHERE object_name='HMS_TODAY' AND object_type='FUNCTION';
 IF n=1 THEN EXECUTE IMMEDIATE 'SELECT HMS_Today() FROM dual' INTO v_today;
 ELSE SELECT TRUNC(CAST(SYSTIMESTAMP AT TIME ZONE 'Asia/Kolkata' AS DATE)) INTO v_today FROM dual; END IF;
 SELECT COUNT(*) INTO n FROM Room r WHERE (r.availability_status='Occupied' AND NOT EXISTS (SELECT 1 FROM Admission a WHERE a.room_id=r.room_id AND a.discharge_date IS NULL)) OR (r.availability_status<>'Occupied' AND EXISTS (SELECT 1 FROM Admission a WHERE a.room_id=r.room_id AND a.discharge_date IS NULL));
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: room state'); END IF;
 SELECT COUNT(*) INTO n FROM Admission a WHERE a.discharge_date IS NULL AND NOT EXISTS (SELECT 1 FROM Admission_Room_Stay s WHERE s.admission_id=a.admission_id AND s.room_id=a.room_id AND s.is_active='Y');
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: missing current observation'); END IF;
 SELECT COUNT(*) INTO n FROM Admission_Room_Stay s JOIN Admission a ON a.admission_id=s.admission_id WHERE s.is_active='Y' AND (a.discharge_date IS NOT NULL OR a.room_id<>s.room_id);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: orphan active observation'); END IF;
 SELECT COUNT(*) INTO n FROM (SELECT patient_id FROM Admission WHERE discharge_date IS NULL GROUP BY patient_id HAVING COUNT(*)>1 UNION ALL SELECT room_id FROM Admission WHERE discharge_date IS NULL GROUP BY room_id HAVING COUNT(*)>1);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: duplicate current admissions'); END IF;
 SELECT COUNT(*) INTO n FROM (SELECT admission_id FROM Admission_Room_Stay WHERE is_active='Y' GROUP BY admission_id HAVING COUNT(*)>1 UNION ALL SELECT room_id FROM Admission_Room_Stay WHERE is_active='Y' GROUP BY room_id HAVING COUNT(*)>1);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: duplicate current observations'); END IF;
 SELECT COUNT(*) INTO n FROM Bill b WHERE b.total_amount+NVL((SELECT SUM(line_total) FROM Bill_Item i WHERE i.bill_id=b.bill_id),0)>999999999.99 OR NVL((SELECT SUM(amount) FROM Bill_Payment p WHERE p.bill_id=b.bill_id),0)>b.total_amount+NVL((SELECT SUM(line_total) FROM Bill_Item i WHERE i.bill_id=b.bill_id),0);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: overpaid or oversized invoices'); END IF;
 SELECT COUNT(*) INTO n FROM Bill_Item WHERE quantity>100000 OR line_total>99999999.99;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: oversized lines'); END IF;
 SELECT COUNT(*) INTO n FROM Bill_Payment WHERE amount>99999999.99;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: oversized payments'); END IF;
 SELECT COUNT(*) INTO n FROM (SELECT admission_date d FROM Admission UNION ALL SELECT discharge_date FROM Admission UNION ALL SELECT bill_date FROM Bill UNION ALL SELECT prescription_date FROM Prescription UNION ALL SELECT date_of_birth FROM Patient UNION ALL SELECT appointment_date FROM Appointment) WHERE d<>TRUNC(d);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: non-day clinical dates'); END IF;
 SELECT COUNT(*) INTO n FROM (SELECT admission_date d FROM Admission UNION ALL SELECT discharge_date FROM Admission UNION ALL SELECT bill_date FROM Bill UNION ALL SELECT prescription_date FROM Prescription UNION ALL SELECT date_of_birth FROM Patient) WHERE d>v_today;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: future clinical dates'); END IF;
 SELECT COUNT(*) INTO n FROM Appointment a JOIN Appointment b ON a.appointment_id<b.appointment_id AND a.appointment_date=b.appointment_date AND (a.doctor_id=b.doctor_id OR a.patient_id=b.patient_id) WHERE a.status IN ('Scheduled','Checked In','Waiting','In Consultation') AND b.status IN ('Scheduled','Checked In','Waiting','In Consultation') AND TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(a.appointment_time,4,2))<TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(b.appointment_time,4,2))+b.duration_minutes AND TO_NUMBER(SUBSTR(b.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(b.appointment_time,4,2))<TO_NUMBER(SUBSTR(a.appointment_time,1,2))*60+TO_NUMBER(SUBSTR(a.appointment_time,4,2))+a.duration_minutes;
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Integrity failure: overlapping patient or doctor appointments'); END IF;
 SELECT COUNT(*) INTO n FROM (SELECT LOWER(idempotency_key) FROM Bill_Payment GROUP BY LOWER(idempotency_key) HAVING COUNT(*)>1);
 IF n<>0 THEN RAISE_APPLICATION_ERROR(-20141,'Duplicate case-normalized payment request keys.'); END IF;
END;
/
