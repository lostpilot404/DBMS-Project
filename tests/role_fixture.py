"""Persisted SQLite SQL-compatibility test double. NEVER an Oracle alternative.

Only application tests use this adapter. It cannot certify Oracle DDL, locks,
compound triggers, NUMBER precision, permissions or migrations.
"""

import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime

from werkzeug.security import generate_password_hash

DDL = """
CREATE TABLE HMS_Write_Mutex(mutex_id INTEGER PRIMARY KEY);INSERT INTO HMS_Write_Mutex VALUES(1);
CREATE TABLE HMS_Settings(singleton INTEGER PRIMARY KEY,hospital_timezone TEXT,schema_version INTEGER,multiuser_version INTEGER,consultation_fee NUMERIC);
INSERT INTO HMS_Settings VALUES(1,'Asia/Kolkata',6,1,20);
CREATE TABLE Department(department_id INTEGER PRIMARY KEY,department_name TEXT UNIQUE,location TEXT);
CREATE TABLE Doctor(doctor_id INTEGER PRIMARY KEY,doctor_name TEXT,specialization TEXT,department_id INTEGER REFERENCES Department,phone TEXT,email TEXT);
CREATE TABLE Patient(patient_id INTEGER PRIMARY KEY,patient_name TEXT,date_of_birth TEXT,gender TEXT,phone TEXT,address TEXT,blood_group TEXT);
CREATE TABLE Room(room_id INTEGER PRIMARY KEY,room_number TEXT,room_type TEXT,availability_status TEXT DEFAULT 'Available');
CREATE TABLE Appointment(appointment_id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES Patient,doctor_id INTEGER REFERENCES Doctor,appointment_date TEXT,appointment_time TEXT,duration_minutes INTEGER DEFAULT 30,status TEXT DEFAULT 'Scheduled');
CREATE TABLE Admission(admission_id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES Patient,room_id INTEGER REFERENCES Room,admission_date TEXT,discharge_date TEXT);
CREATE UNIQUE INDEX uq_active_patient ON Admission(patient_id) WHERE discharge_date IS NULL;
CREATE UNIQUE INDEX uq_active_room ON Admission(room_id) WHERE discharge_date IS NULL;
CREATE TABLE Admission_Room_Stay(stay_id INTEGER PRIMARY KEY,admission_id INTEGER REFERENCES Admission,room_id INTEGER REFERENCES Room,started_at TEXT,ended_at TEXT,is_active TEXT,source TEXT,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TRIGGER fixture_admit AFTER INSERT ON Admission BEGIN
 UPDATE Room SET availability_status='Occupied' WHERE room_id=NEW.room_id;
 INSERT INTO Admission_Room_Stay(admission_id,room_id,started_at,is_active,source) VALUES(NEW.admission_id,NEW.room_id,CURRENT_TIMESTAMP,'Y','LIVE');END;
CREATE TRIGGER fixture_transfer AFTER UPDATE ON Admission WHEN OLD.room_id<>NEW.room_id OR NEW.discharge_date IS NOT NULL BEGIN
 UPDATE Room SET availability_status='Available' WHERE room_id=OLD.room_id;
 UPDATE Admission_Room_Stay SET is_active='N',ended_at=CURRENT_TIMESTAMP WHERE admission_id=OLD.admission_id AND is_active='Y';
 INSERT INTO Admission_Room_Stay(admission_id,room_id,started_at,is_active,source) SELECT NEW.admission_id,NEW.room_id,CURRENT_TIMESTAMP,'Y','LIVE' WHERE NEW.discharge_date IS NULL;
 UPDATE Room SET availability_status='Occupied' WHERE room_id=NEW.room_id AND NEW.discharge_date IS NULL;END;
CREATE TABLE Medicine(medicine_id INTEGER PRIMARY KEY,medicine_name TEXT,manufacturer TEXT,price NUMERIC DEFAULT 0,stock_quantity INTEGER DEFAULT 0 CHECK(stock_quantity>=0));
CREATE TABLE HMS_Staff(staff_id INTEGER PRIMARY KEY,full_name TEXT,staff_kind TEXT,phone TEXT,is_active TEXT DEFAULT 'Y');
CREATE TABLE HMS_User(user_id INTEGER PRIMARY KEY,username TEXT UNIQUE,password_hash TEXT,role TEXT,patient_id INTEGER UNIQUE REFERENCES Patient,doctor_id INTEGER UNIQUE REFERENCES Doctor,staff_id INTEGER UNIQUE REFERENCES HMS_Staff,is_active TEXT DEFAULT 'Y');
CREATE TABLE HMS_Session(token_hash TEXT PRIMARY KEY,user_id INTEGER REFERENCES HMS_User,csrf_token TEXT,expires_at TEXT);
CREATE TABLE HMS_Audit(audit_id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES HMS_User,action TEXT,entity TEXT,record_id INTEGER,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE HMS_Care_Assignment(assignment_id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES Patient,doctor_id INTEGER REFERENCES Doctor,is_active TEXT DEFAULT 'Y',UNIQUE(patient_id,doctor_id));
CREATE TABLE HMS_Ward_Assignment(assignment_id INTEGER PRIMARY KEY,admission_id INTEGER REFERENCES Admission,user_id INTEGER REFERENCES HMS_User,is_active TEXT DEFAULT 'Y',UNIQUE(admission_id,user_id));
CREATE TABLE HMS_Encounter(encounter_id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES Patient,doctor_id INTEGER REFERENCES Doctor,appointment_id INTEGER UNIQUE REFERENCES Appointment,admission_id INTEGER REFERENCES Admission,diagnosis TEXT,clinical_notes TEXT,status TEXT DEFAULT 'Open',recorded_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE Prescription(prescription_id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES Patient,doctor_id INTEGER REFERENCES Doctor,medicine_id INTEGER REFERENCES Medicine,dosage TEXT,duration TEXT,prescription_date TEXT,encounter_id INTEGER REFERENCES HMS_Encounter,ordered_quantity INTEGER);
CREATE TABLE HMS_Observation(observation_id INTEGER PRIMARY KEY,admission_id INTEGER REFERENCES Admission,user_id INTEGER REFERENCES HMS_User,observation TEXT,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE HMS_Test_Catalog(test_id INTEGER PRIMARY KEY,test_name TEXT UNIQUE,fee NUMERIC,is_active TEXT DEFAULT 'Y');
CREATE TABLE HMS_Test_Order(order_id INTEGER PRIMARY KEY,encounter_id INTEGER REFERENCES HMS_Encounter,test_id INTEGER REFERENCES HMS_Test_Catalog,status TEXT DEFAULT 'Ordered',ordered_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE HMS_Test_Result(result_id INTEGER PRIMARY KEY,order_id INTEGER UNIQUE REFERENCES HMS_Test_Order,user_id INTEGER REFERENCES HMS_User,result_text TEXT,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE HMS_Appointment_Request(request_id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES Patient,doctor_id INTEGER REFERENCES Doctor,requested_date TEXT,requested_time TEXT,reason TEXT,status TEXT DEFAULT 'Pending',appointment_id INTEGER REFERENCES Appointment,encounter_id INTEGER REFERENCES HMS_Encounter);
CREATE TABLE HMS_Medicine_Batch(batch_id INTEGER PRIMARY KEY,medicine_id INTEGER REFERENCES Medicine,batch_number TEXT,expires_on TEXT,quantity INTEGER CHECK(quantity>=0),UNIQUE(medicine_id,batch_number));
CREATE TABLE HMS_Dispense(dispense_id INTEGER PRIMARY KEY,prescription_id INTEGER REFERENCES Prescription,batch_id INTEGER REFERENCES HMS_Medicine_Batch,user_id INTEGER REFERENCES HMS_User,quantity INTEGER,idempotency_key TEXT UNIQUE,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE Bill(bill_id INTEGER PRIMARY KEY,patient_id INTEGER REFERENCES Patient,bill_date TEXT,consultation_charge NUMERIC DEFAULT 0,room_charge NUMERIC DEFAULT 0,medicine_charge NUMERIC DEFAULT 0,total_amount NUMERIC GENERATED ALWAYS AS(consultation_charge+room_charge+medicine_charge) VIRTUAL,payment_status TEXT DEFAULT 'Pending',notes TEXT,encounter_id INTEGER REFERENCES HMS_Encounter,admission_id INTEGER REFERENCES Admission);
CREATE TABLE Bill_Item(item_id INTEGER PRIMARY KEY,bill_id INTEGER REFERENCES Bill,description TEXT,quantity INTEGER,unit_price NUMERIC,line_total NUMERIC GENERATED ALWAYS AS(quantity*unit_price) VIRTUAL);
CREATE TABLE Bill_Payment(payment_id INTEGER PRIMARY KEY,bill_id INTEGER REFERENCES Bill,amount NUMERIC,payment_method TEXT,reference TEXT,idempotency_key TEXT UNIQUE,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,recorded_timezone TEXT DEFAULT 'UTC');
CREATE TABLE HMS_Care_Charge(charge_id INTEGER PRIMARY KEY,encounter_id INTEGER REFERENCES HMS_Encounter,source_kind TEXT,source_id INTEGER,description TEXT,quantity INTEGER,unit_price NUMERIC,bill_item_id INTEGER UNIQUE REFERENCES Bill_Item,UNIQUE(source_kind,source_id));
CREATE TABLE HMS_Maintenance_Task(task_id INTEGER PRIMARY KEY,room_id INTEGER REFERENCES Room,description TEXT,status TEXT DEFAULT 'Open',created_by INTEGER REFERENCES HMS_User,completed_by INTEGER REFERENCES HMS_User);
CREATE TABLE HMS_Operation(operation_key TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES HMS_User,action TEXT NOT NULL,payload_hash TEXT NOT NULL,result_id INTEGER NOT NULL,reason TEXT NOT NULL,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL);
CREATE TABLE HMS_Amendment(amendment_id INTEGER PRIMARY KEY,encounter_id INTEGER REFERENCES HMS_Encounter,result_id INTEGER REFERENCES HMS_Test_Result,content TEXT NOT NULL,reason TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES HMS_User,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL,CHECK((encounter_id IS NOT NULL AND result_id IS NULL) OR (encounter_id IS NULL AND result_id IS NOT NULL)));
CREATE TABLE HMS_Order_Cancel(cancellation_id INTEGER PRIMARY KEY,prescription_id INTEGER UNIQUE REFERENCES Prescription,order_id INTEGER UNIQUE REFERENCES HMS_Test_Order,reason TEXT NOT NULL,user_id INTEGER NOT NULL REFERENCES HMS_User,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL,CHECK((prescription_id IS NOT NULL AND order_id IS NULL) OR (prescription_id IS NULL AND order_id IS NOT NULL)));
CREATE TABLE HMS_Stock_Opening(batch_id INTEGER PRIMARY KEY REFERENCES HMS_Medicine_Batch,quantity INTEGER NOT NULL CHECK(quantity>=0),recorded_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL);
CREATE TABLE HMS_Legacy_Stock(medicine_id INTEGER PRIMARY KEY REFERENCES Medicine,quantity INTEGER NOT NULL CHECK(quantity>=0),recorded_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL);
CREATE TABLE HMS_Stock_Event(event_id INTEGER PRIMARY KEY,event_kind TEXT NOT NULL CHECK(event_kind IN ('RECEIPT','RETURN_RESTOCK','RETURN_QUARANTINE','WRITE_OFF','ADJUST_ADD','ADJUST_REMOVE')),medicine_id INTEGER NOT NULL REFERENCES Medicine,batch_id INTEGER NOT NULL REFERENCES HMS_Medicine_Batch,dispense_id INTEGER REFERENCES HMS_Dispense,quantity INTEGER NOT NULL CHECK(quantity>0),user_id INTEGER NOT NULL REFERENCES HMS_User,reason TEXT NOT NULL,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL,CHECK((event_kind IN ('RETURN_RESTOCK','RETURN_QUARANTINE') AND dispense_id IS NOT NULL) OR (event_kind NOT IN ('RETURN_RESTOCK','RETURN_QUARANTINE') AND dispense_id IS NULL)));
CREATE TABLE HMS_Fin_Event(event_id INTEGER PRIMARY KEY,bill_id INTEGER NOT NULL REFERENCES Bill,event_kind TEXT NOT NULL CHECK(event_kind IN ('CREDIT','DEBIT','WRITE_OFF','REFUND','REFUND_CREDIT','VOID')),amount NUMERIC NOT NULL CHECK(amount>0),payment_id INTEGER REFERENCES Bill_Payment,related_event_id INTEGER REFERENCES HMS_Fin_Event,stock_event_id INTEGER REFERENCES HMS_Stock_Event,user_id INTEGER NOT NULL REFERENCES HMS_User,reason TEXT NOT NULL,recorded_at TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL,CHECK((event_kind='REFUND' AND payment_id IS NOT NULL) OR (event_kind<>'REFUND' AND payment_id IS NULL)),CHECK((event_kind='REFUND_CREDIT' AND related_event_id IS NOT NULL) OR (event_kind<>'REFUND_CREDIT' AND related_event_id IS NULL)));
-- SQLite NUMERIC is binary floating-point: emulate the Oracle cents boundary explicitly.
CREATE VIEW V_Invoice_Balances AS
SELECT x.*,ROUND(x.gross_billed+x.debits-x.credits-x.written_off,2) billed,ROUND(x.gross_paid-x.refunds,2) paid,
 ROUND(x.gross_billed+x.debits-x.credits-x.written_off-x.gross_paid+x.refunds,2) balance,
 CASE WHEN x.void_count>0 THEN 'Voided'
 WHEN ROUND(x.gross_billed+x.debits-x.credits-x.written_off,2)=ROUND(x.gross_paid-x.refunds,2) THEN 'Paid'
 WHEN ROUND(x.gross_paid,2)=ROUND(x.refunds,2) THEN 'Unpaid' ELSE 'Partial' END ledger_status
FROM (SELECT b.bill_id,b.patient_id,b.bill_date,b.notes,b.consultation_charge,b.room_charge,b.medicine_charge,
 b.payment_status legacy_status,b.total_amount legacy_charges,COALESCE(i.item_total,0) item_total,
 ROUND(b.total_amount+COALESCE(i.item_total,0),2) gross_billed,COALESCE(p.paid_total,0) gross_paid,
 COALESCE(f.debits,0) debits,COALESCE(f.credits,0) credits,COALESCE(f.written_off,0) written_off,COALESCE(f.refunds,0) refunds,
 COALESCE(f.void_count,0) void_count,COALESCE(f.correction_count,0) correction_count
 FROM Bill b LEFT JOIN(SELECT bill_id,SUM(line_total) item_total FROM Bill_Item GROUP BY bill_id)i ON i.bill_id=b.bill_id
 LEFT JOIN(SELECT bill_id,SUM(amount) paid_total FROM Bill_Payment GROUP BY bill_id)p ON p.bill_id=b.bill_id
 LEFT JOIN(SELECT bill_id,SUM(CASE WHEN event_kind='DEBIT' THEN amount ELSE 0 END) debits,
 SUM(CASE WHEN event_kind IN ('CREDIT','REFUND_CREDIT','VOID') THEN amount ELSE 0 END) credits,
 SUM(CASE WHEN event_kind='WRITE_OFF' THEN amount ELSE 0 END) written_off,
 SUM(CASE WHEN event_kind='REFUND' THEN amount ELSE 0 END) refunds,
 SUM(CASE WHEN event_kind='VOID' THEN 1 ELSE 0 END) void_count,COUNT(*) correction_count
 FROM HMS_Fin_Event GROUP BY bill_id)f ON f.bill_id=b.bill_id)x;
CREATE VIEW V_HMS_Cash_Events AS
 SELECT bill_id,amount,recorded_at,recorded_timezone FROM Bill_Payment
 UNION ALL SELECT bill_id,-amount,recorded_at,'UTC' FROM HMS_Fin_Event WHERE event_kind='REFUND';
CREATE VIEW V_HMS_Batch_Recon AS
SELECT b.batch_id,b.medicine_id,b.quantity,
 COALESCE(o.quantity,0)+COALESCE(s.net_quantity,0)-COALESCE(d.dispensed,0) expected_quantity,
 b.quantity-COALESCE(o.quantity,0)-COALESCE(s.net_quantity,0)+COALESCE(d.dispensed,0) difference
FROM HMS_Medicine_Batch b LEFT JOIN HMS_Stock_Opening o ON o.batch_id=b.batch_id
LEFT JOIN(SELECT batch_id,SUM(CASE WHEN event_kind IN ('RECEIPT','RETURN_RESTOCK','ADJUST_ADD') THEN quantity
 WHEN event_kind IN ('WRITE_OFF','ADJUST_REMOVE') THEN -quantity ELSE 0 END) net_quantity
 FROM HMS_Stock_Event GROUP BY batch_id)s ON s.batch_id=b.batch_id
LEFT JOIN(SELECT batch_id,SUM(quantity) dispensed FROM HMS_Dispense CROSS JOIN HMS_Settings
 WHERE dispense_id>stock_cutover_id GROUP BY batch_id)d ON d.batch_id=b.batch_id;
CREATE VIEW V_HMS_Medicine_Recon AS
SELECT m.medicine_id,m.stock_quantity,COALESCE(l.quantity,0) legacy_quantity,
 COALESCE(l.quantity,0)+COALESCE(b.quantity,0) expected_quantity,
 m.stock_quantity-COALESCE(l.quantity,0)-COALESCE(b.quantity,0) difference
FROM Medicine m LEFT JOIN HMS_Legacy_Stock l ON l.medicine_id=m.medicine_id
LEFT JOIN(SELECT medicine_id,SUM(quantity) quantity FROM HMS_Medicine_Batch GROUP BY medicine_id)b ON b.medicine_id=m.medicine_id;
CREATE VIEW V_HMS_Care_Net AS
SELECT c.charge_id,c.encounter_id,c.source_kind,c.source_id,c.description,c.unit_price,c.bill_item_id,
 c.quantity-COALESCE(r.returned_quantity,0) quantity
FROM HMS_Care_Charge c LEFT JOIN(SELECT dispense_id,SUM(quantity) returned_quantity
 FROM HMS_Stock_Event WHERE event_kind IN ('RETURN_RESTOCK','RETURN_QUARANTINE') GROUP BY dispense_id)r
 ON c.source_kind='Dispense' AND r.dispense_id=c.source_id
WHERE NOT EXISTS(SELECT 1 FROM HMS_Order_Cancel x WHERE c.source_kind='Test' AND x.order_id=c.source_id);
CREATE VIEW V_HMS_Return_Review AS
SELECT s.event_id,i.bill_id,b.patient_id,s.dispense_id,s.quantity,c.unit_price,
 s.quantity*c.unit_price eligible_credit,COALESCE(f.credited,0) credited,
 s.quantity*c.unit_price-COALESCE(f.credited,0) remaining_credit
FROM HMS_Stock_Event s JOIN HMS_Care_Charge c ON c.source_kind='Dispense' AND c.source_id=s.dispense_id
JOIN Bill_Item i ON i.item_id=c.bill_item_id JOIN Bill b ON b.bill_id=i.bill_id
LEFT JOIN(SELECT stock_event_id,SUM(amount) credited FROM HMS_Fin_Event
 WHERE event_kind IN ('CREDIT','REFUND_CREDIT','WRITE_OFF') GROUP BY stock_event_id)f ON f.stock_event_id=s.event_id
WHERE s.event_kind IN ('RETURN_RESTOCK','RETURN_QUARANTINE');
"""


class Variable:
    def __init__(self):
        self.value = None

    def getvalue(self):
        return self.value


class Cursor:
    def __init__(self, db):
        self.db = db
        self.cur = db.sql.cursor()
        self.description = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cur.close()

    def var(self, kind):
        return Variable()

    def execute(self, sql, binds=None):
        self.db.calls.append((sql, binds or {}))
        binds = dict(binds or {})
        if sql == "SET TRANSACTION READ ONLY":
            return self
        sql = re.sub(r" FOR UPDATE(?: WAIT \d+)?", "", sql, flags=re.I)
        sql = re.sub(r"NVL\(", "COALESCE(", sql, flags=re.I)
        sql = sql.replace("HMS_Today()+30", "datetime(HMS_Today(), '+30 days')")
        # Test-only translation, not Oracle execution/precision or timezone certification.
        sql = sql.replace(
            "TRUNC(CASE WHEN pay.recorded_timezone='UTC' THEN CAST(FROM_TZ(pay.recorded_at,'UTC') AT TIME ZONE cfg.hospital_timezone AS DATE) ELSE CAST(pay.recorded_at AS DATE) END,'MM')",
            "HMS_TEST_MONTH(pay.recorded_at,pay.recorded_timezone,cfg.hospital_timezone)",
        )
        sql = sql.replace("TRUNC(bill_date,'MM')", "(substr(bill_date,1,7)||'-01')")
        sql = re.sub(
            r"OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY",
            "LIMIT :limit OFFSET :offset",
            sql,
            flags=re.I,
        )
        sql = re.sub(
            r"OFFSET :page_offset ROWS FETCH NEXT :page_size ROWS ONLY",
            "LIMIT :page_size OFFSET :page_offset",
            sql,
            flags=re.I,
        )
        sql = re.sub(r"FETCH FIRST (\d+) ROWS ONLY", r"LIMIT \1", sql, flags=re.I)
        sql = sql.replace("FROM dual", "").replace("FROM DUAL", "")
        returning = re.search(r" RETURNING \w+ INTO :out_id", sql, re.I)
        out = binds.pop("out_id", None)
        if returning:
            sql = sql[: returning.start()]
        from decimal import Decimal

        for k, v in binds.items():
            if isinstance(v, Decimal):
                binds[k] = str(v)
            elif isinstance(v, datetime):
                binds[k] = v.isoformat(" ")
            elif isinstance(v, date):
                binds[k] = datetime.combine(v, datetime.min.time()).isoformat(" ")
        self.cur.execute(sql, binds)
        self.description = self.cur.description
        self.rowcount = self.cur.rowcount
        if out:
            out.value = self.cur.lastrowid
        return self

    def convert(self, row):
        if row is None:
            return None
        result = []
        for desc, v in zip(self.description or [], row):
            if v is not None and desc[0].lower() in (
                "appointment_date",
                "admission_date",
                "discharge_date",
                "bill_date",
                "date_of_birth",
                "prescription_date",
                "requested_date",
                "expires_on",
                "hms_today()",
            ):
                v = datetime.fromisoformat(str(v))
            result.append(v)
        return tuple(result)

    def fetchone(self):
        return self.convert(self.cur.fetchone())

    def fetchall(self):
        return [self.convert(r) for r in self.cur.fetchall()]


class Connection:
    def __init__(self, db):
        self.db = db

    def cursor(self):
        return Cursor(self.db)

    def commit(self):
        self.db.sql.commit()

    def rollback(self):
        self.db.sql.rollback()


class RoleDatabase:
    def __init__(self, path=":memory:", seed=True):
        self.sql = sqlite3.connect(path, check_same_thread=False)
        self.sql.execute("PRAGMA foreign_keys=ON")
        self.lock = threading.RLock()
        self.calls = []
        from hms.api import hospital_today

        self.sql.create_function("HMS_Today", 0, lambda: datetime.combine(hospital_today(),datetime.min.time()).isoformat(" "))
        self.sql.create_function("TO_NUMBER", 1, lambda v: int(v))

        def receipt_month(value, basis, zone):
            from datetime import timezone
            from zoneinfo import ZoneInfo

            stamp = datetime.fromisoformat(str(value))
            if basis == "UTC":
                stamp = stamp.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(zone))
            return stamp.strftime("%Y-%m-01")

        self.sql.create_function("HMS_TEST_MONTH", 3, receipt_month)
        self.sql.executescript(DDL)
        self.sql.execute(
            "ALTER TABLE HMS_Settings ADD correction_version INTEGER DEFAULT 1"
        )
        self.sql.execute(
            "ALTER TABLE HMS_Settings ADD stock_cutover_id INTEGER DEFAULT 0"
        )
        if seed:
            self.seed()

    @contextmanager
    def connection(self):
        with self.lock:
            yield Connection(self)

    def seed(self):
        self.sql.executescript(
            "INSERT INTO Department VALUES(1,'Demo','Lab'); INSERT INTO Doctor VALUES(1,'Doctor One','Demo',1,NULL,NULL);INSERT INTO Doctor VALUES(2,'Doctor Two','Demo',1,NULL,NULL);INSERT INTO Patient VALUES(1,'Patient One','2000-01-01','O',NULL,NULL,NULL);INSERT INTO Patient VALUES(2,'Patient Two','2001-01-01','O',NULL,NULL,NULL); INSERT INTO Room VALUES(1,'A1','General','Available'); INSERT INTO Room VALUES(2,'A2','General','Available');INSERT INTO Medicine VALUES(1,'Test Medicine','Synthetic',5,0);INSERT INTO HMS_Test_Catalog VALUES(1,'Synthetic blood test',30,'Y');"
        )
        from hms.auth import ROLES

        encoded = generate_password_hash("fixture-password-only", method="scrypt")
        for i, role in enumerate(ROLES, 1):
            self.sql.execute(
                "INSERT INTO HMS_Staff VALUES(?,?,?,?,?)",
                (i, role + " fixture", role, None, "Y"),
            )
            self.sql.execute(
                "INSERT INTO HMS_User VALUES(?,?,?,?,?,?,?,?)",
                (
                    i,
                    role,
                    encoded,
                    role,
                    1 if role == "patient" else None,
                    1 if role == "doctor" else None,
                    i if role not in ("doctor", "patient") else None,
                    "Y",
                ),
            )
        self.sql.execute(
            "INSERT INTO HMS_User VALUES(20,'patient2',?,'patient',2,NULL,NULL,'Y')",
            (encoded,),
        )
        self.sql.execute(
            "INSERT INTO HMS_User VALUES(21,'doctor2',?,'doctor',NULL,2,NULL,'Y')",
            (encoded,),
        )
        self.sql.commit()
