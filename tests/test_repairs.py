"""Campaign regressions: source contracts are NOT Oracle execution evidence."""
import os
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from hms import create_app
from hms.api import _json_value, _patient_timeline
from tests.test_app import FakeConnection, FakeCursor, FakeDatabase

KEY = '11111111-1111-4111-8111-111111111111'

class LedgerCursor(FakeCursor):
    def execute(self, sql, binds=None):
        self.database.raw_calls.append((sql, binds or {}))
        if 'FROM Bill_Payment WHERE LOWER(idempotency_key)' in sql:
            self.database.calls.append((sql, binds or {}))
            self._one = self.database.existing
            return self
        return super().execute(sql, binds)

class LedgerConnection(FakeConnection):
    def cursor(self):
        return LedgerCursor(self.database)

class LedgerDatabase(FakeDatabase):
    def __init__(self):
        super().__init__()
        self.existing = None
        self.raw_calls = []
    @contextmanager
    def connection(self):
        self.connection_count += 1
        yield LedgerConnection(self)

class RepairApiTests(unittest.TestCase):
    def setUp(self):
        self.db = LedgerDatabase()
        self.client = create_app(database=self.db, test_config={'TESTING': True, 'AUTH_REQUIRED': False}).test_client()
    def payment(self, **changes):
        body = dict(amount='40.00', payment_method='Cash', reference='  demo  ', idempotency_key=KEY)
        body.update(changes)
        return self.client.post('/api/bills/1/payments', json=body)
    def test_replay_returns_original_even_if_invoice_is_now_settled(self):
        self.db.existing = (7, 1, Decimal('40.00'), 'Cash', 'demo')
        self.db.bill_paid = Decimal('100')
        response = self.payment()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['data'], {'id': 7, 'replayed': True})
        self.assertFalse(any(sql.startswith('INSERT') for sql, _ in self.db.calls))
    def test_changed_replay_is_explicit_conflict(self):
        self.db.existing = (7, 1, Decimal('40'), 'Cash', 'demo')
        response = self.payment(amount='41')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['error']['code'], 'idempotency_mismatch')
    def test_other_invoice_cannot_reuse_request_key(self):
        self.db.existing = (7, 2, Decimal('40'), 'Cash', 'demo')
        self.assertEqual(self.payment().status_code, 409)
    def test_invoice_date_and_legacy_status_are_immutable(self):
        for payload in ({'bill_date': '2020-01-01'}, {'payment_status':'Paid'}):
            with self.subTest(payload=payload):
                r = self.client.put('/api/bills/1', json=payload)
                self.assertEqual(r.status_code, 409)
                self.assertEqual(r.get_json()['error']['code'], 'invoice_history')
    def test_notes_remain_editable_after_payment(self):
        self.db.bill_paid = Decimal('40')
        self.assertEqual(self.client.put('/api/bills/1', json={'notes':'Administrative note'}).status_code, 200)
    def test_zero_invoice_is_paid_without_fabricating_payment(self):
        self.db.bill_base = Decimal('0')
        data = self.client.get('/api/bills/1/ledger').get_json()['data']
        self.assertEqual((data['status'],data['balance'],data['payments']), ('Paid','0.00',[]))
    def test_mutations_lock_global_resource_before_bill(self):
        self.payment()
        self.assertIn('HMS_Write_Mutex', self.db.raw_calls[0][0])
    def test_remote_boundary_requires_authentication(self):
        app = create_app(database=self.db, test_config={'TESTING':True, 'AUTH_REQUIRED':False,'DEMO_USERNAME':'demo','DEMO_PASSWORD':'test-only'})
        c = app.test_client()
        self.assertEqual(c.get('/api/patients').status_code,401)
        self.assertEqual(c.get('/api/patients',headers={'Authorization':'Basic ZGVtbzp0ZXN0LW9ubHk='}).status_code,200)
    def test_deadlocks_are_retryable_conflicts(self):
        from tests.test_app import FakeOracleError
        db = FakeDatabase(execute_error=FakeOracleError('ORA-00060: deadlock'))
        r = create_app(database=db, test_config={'TESTING':True, 'AUTH_REQUIRED':False}).test_client().get('/api/health')
        self.assertEqual(r.status_code,409)
    def test_settings_expose_hospital_clock(self):
        r = self.client.get('/api/config')
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.get_json()['data']['timezone'],'Asia/Kolkata')

class ValueContractTests(unittest.TestCase):
    def test_decimal_serialization_is_lossless(self):
        self.assertEqual(_json_value(Decimal('9999999899000000.01')), '9999999899000000.01')
    def test_midnight_uses_hospital_not_host_timezone(self):
        from importlib import import_module
        api = import_module("hms.api")
        today = getattr(api, 'hospital_today', None)
        self.assertTrue(callable(today), 'hospital_today must be shared by date validators')
        self.assertEqual(today(datetime(2026,10,28,19,0,tzinfo=timezone.utc)).isoformat(), '2026-10-29')
    def test_timeline_does_not_relabel_original_room_after_transfer(self):
        related = {'admissions':[{'admission_id':1,'room_number':'NEW','admission_date':'2020-01-01'}],
          'room_assignments':[{'stay_id':1,'admission_id':1,'room_number':'OLD','source':'LEGACY','started_at':None,'ended_at':None,'is_active':'N','recorded_at':'2026-10-28T10:00:00'}]}
        timeline = _patient_timeline(related)
        admission = next(e for e in timeline if e['type']=='Admission')
        self.assertNotIn('NEW', admission['details'])
        self.assertTrue(any('OLD' in e['details'] and 'unknown' in e['details'].lower() for e in timeline))

class SqlContractTests(unittest.TestCase):
    def test_corrective_migration_and_shared_installer_exist(self):
        self.assertTrue(Path('sql/migrations/006_integrity_repair.sql').exists())
        self.assertTrue(Path('sql/05_integrity_objects.sql').exists())
    def test_all_current_financial_queries_use_shared_view(self):
        from hms.api import REPORTS, RESOURCES
        self.assertIn('V_Invoice_Balances',RESOURCES['bills']['select'])
        for name in ('patient-bills','invoice-balances','billing-by-status','monthly-revenue'):
            self.assertIn('V_Invoice_Balances',REPORTS[name]['select'])
    def test_verification_raises_on_invariant_failure(self):
        self.assertIn('RAISE_APPLICATION_ERROR',Path('sql/04_verification.sql').read_text())
    def test_fresh_setup_installs_same_corrective_objects(self):
        self.assertIn('@@05_integrity_objects.sql',Path('sql/01_create_schema.sql').read_text())
    def test_history_deletions_and_projection_bypasses_are_guarded(self):
        p=Path('sql/05_integrity_objects.sql')
        self.assertTrue(p.exists())
        text=p.read_text()
        for token in ('trg_stay_write_guard','trg_room_write_guard','trg_appointment_retain','trg_prescription_retain','trg_bill_retain','HMS_Write_Mutex','HMS_Internal'):
            self.assertIn(token,text)

class AdditionalContractTests(unittest.TestCase):
    def setUp(self):
        self.db = LedgerDatabase()
        self.c = create_app(database=self.db, test_config={'TESTING':True, 'AUTH_REQUIRED':False}).test_client()
    def test_unsupported_reversal_is_explicit(self):
        r=self.c.delete('/api/bills/1/payments/7')
        self.assertEqual(r.status_code,409)
        self.assertEqual(r.get_json()['error']['code'],'reversal_unsupported')
    def test_hospital_settings_mismatch_blocks_readiness(self):
        self.db.hospital_zone='UTC'
        self.assertEqual(self.c.get('/api/health').status_code,503)
    def test_quantity_and_line_limits_match_sql(self):
        for qty,price in [(100001,'1'),(100000,'1000.00')]:
            r=self.c.post('/api/bills/1/items',json={'description':'Synthetic','quantity':qty,'unit_price':price})
            self.assertEqual(r.status_code,400)

class ObservationContractTests(unittest.TestCase):
    def test_midnight_observation_remains_a_timestamp(self):
        from hms.api import _column_value
        self.assertEqual(_column_value('recorded_at',datetime(2026,10,29,0,0)), '2026-10-29T00:00:00')
    def test_money_zero_and_identifiers_have_distinct_encodings(self):
        from hms.api import _column_value
        self.assertEqual(_column_value('balance',0),'0.00')
        self.assertEqual(_column_value('patient_id',Decimal('1')),1)

class DepartmentPreviewTests(unittest.TestCase):
    def test_department_name_preview_is_bounded_not_unbounded_listagg(self):
        from hms.api import RESOURCES
        self.assertIn('dc.rn <= 5',RESOURCES['departments']['select'])

class ResourceCoverageTests(unittest.TestCase):
    def test_every_module_has_a_valid_create_contract(self):
        from hms.api import hospital_today
        day=hospital_today().isoformat()
        payloads={
          'departments':{'department_name':'Synthetic','location':'Test'},
          'doctors':{'doctor_name':'Synthetic','specialization':'Test','department_id':1},
          'patients':{'patient_name':'Synthetic','date_of_birth':'2000-01-01','gender':'O'},
          'appointments':{'patient_id':1,'doctor_id':1,'appointment_date':day,'appointment_time':'09:00'},
          'rooms':{'room_number':'Test','room_type':'General'},
          'admissions':{'patient_id':1,'room_id':1,'admission_date':day},
          'medicines':{'medicine_name':'Synthetic','price':'1.25','stock_quantity':5},
          'prescriptions':{'patient_id':1,'doctor_id':1,'medicine_id':1,'dosage':'One','duration':'Day','prescription_date':day},
          'bills':{'patient_id':1,'bill_date':day,'consultation_charge':'1.00','room_charge':'0','medicine_charge':'0','notes':'Synthetic'}}
        for resource,body in payloads.items():
            with self.subTest(resource=resource):
                db=LedgerDatabase();c=create_app(database=db,test_config={'TESTING':True, 'AUTH_REQUIRED':False}).test_client()
                r=c.post('/api/'+resource,json=body)
                self.assertEqual(r.status_code,201,r.get_json())
                self.assertEqual(db.commits,1)
                self.assertIn('HMS_Write_Mutex',db.raw_calls[0][0])
    def test_all_fourteen_reports_and_csv_routes_execute_allowlisted_queries(self):
        from hms.api import REPORTS
        self.assertEqual(len(REPORTS),14)
        c=create_app(database=FakeDatabase(),test_config={'TESTING':True, 'AUTH_REQUIRED':False}).test_client()
        for name in REPORTS:
            with self.subTest(report=name):
                r=c.get('/api/reports/'+name)
                self.assertEqual(r.status_code,200,r.get_json())
                csv=c.get('/api/reports/'+name+'/csv')
                self.assertEqual(csv.status_code,200)

class EntryPointSafetyTests(unittest.TestCase):
    def test_remote_debugger_is_refused_even_with_demo_credentials(self):
        import runpy
        with patch.dict(os.environ,{'HMS_HOST':'0.0.0.0','DEMO_USERNAME':'demo','DEMO_PASSWORD':'synthetic-test','FLASK_DEBUG':'true'}):
            with patch('flask.Flask.run'), self.assertRaises(RuntimeError):
                runpy.run_path('app.py',run_name='__main__')

class LegacyKeyCaseTests(unittest.TestCase):
    def test_legacy_uppercase_uuid_lookup_is_case_normalized(self):
        db=LedgerDatabase();db.existing=(7,1,Decimal('40'),'Cash','demo')
        c=create_app(database=db,test_config={'TESTING':True, 'AUTH_REQUIRED':False}).test_client()
        r=c.post('/api/bills/1/payments',json={'amount':'40','payment_method':'Cash','reference':'demo','idempotency_key':KEY.upper()})
        self.assertEqual(r.status_code,200)
        self.assertTrue(any('LOWER(idempotency_key)' in sql for sql,_ in db.raw_calls))
    def test_database_has_case_normalized_key_uniqueness(self):
        self.assertIn('CREATE UNIQUE INDEX uq_payment_request_norm',Path('sql/05_integrity_objects.sql').read_text())

class TimelineLedgerTests(unittest.TestCase):
    def test_patient_bill_event_includes_recorded_payments_and_balance(self):
        event=_patient_timeline({'bills':[{'bill_id':1,'bill_date':'2026-10-29','total_amount':'125.00','paid':'40.00','balance':'85.00','payment_status':'Partial'}]})[0]
        self.assertIn('40.00',event['details'])
        self.assertIn('85.00',event['details'])

class IntegerMoneyBoundaryTests(unittest.TestCase):
    def test_integer_zero_from_driver_remains_string_money(self):
        db=LedgerDatabase();db.bill_base=0
        c=create_app(database=db,test_config={'TESTING':True, 'AUTH_REQUIRED':False}).test_client()
        self.assertEqual(c.get('/api/bills/1/ledger').get_json()['data']['legacy_charge_total'],'0.00')

if __name__ == '__main__': unittest.main()
