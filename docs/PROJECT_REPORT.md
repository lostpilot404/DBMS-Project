# Hospital Management System

**Course:** BCSE302P — Database Systems<br>
**Database:** Oracle Database 12c+<br>
**Interface:** HTML5, CSS3, JavaScript<br>
**Backend:** Python 3 / Flask / `python-oracledb`

> **Requirements-source note:** The 13-page source report (`R1.pdf`) was not available during initial implementation but was supplied for the pre-publication audit. Its extractable scope, nine table definitions, key relationships, and 3NF objective were compared against the implementation. The nine-entity model aligns; this implementation refines several data-type sizes and adds application and integrity safeguards. The report's diagram artwork and team/contact details are not reproduced or evaluated in this report.

## 1. Overview and scope

This project demonstrates a relational hospital information system for departments, doctors, patients, appointments, rooms, admissions, medicines, prescriptions, and patient bills. It includes a nine-table Oracle schema, integrity constraints, illustrative fictional records, reporting queries, a JSON API, and a responsive browser interface.

The application is an educational project, not a clinical or financial production system. It does not provide authentication, role-based access, audit history, electronic prescribing safeguards, payment processing, or a dispensing ledger.

## 2. Architecture

```text
HTML / CSS / JavaScript browser
          │ relative same-origin /api/* JSON requests
          ▼
Flask application (validation, CRUD, transactions, error mapping)
          │ python-oracledb Thin driver + parameterized SQL
          ▼
Oracle Database (constraints, indexes, virtual columns, triggers)
```

The browser does not hold credentials or connect to Oracle. Configuration is read from local environment variables (optionally `.env` for development). Successful mutations commit; exceptions roll back. Oracle integrity errors are translated into safe, structured HTTP responses and do not return SQL text or stack traces to the browser.

## 3. ER model and relationship summary

The editable diagram is [`ER_DIAGRAM.mmd`](ER_DIAGRAM.mmd). It matches the implemented nine-table schema.

- One **Department** has zero or more **Doctors**; each doctor is assigned to exactly one department.
- One **Patient** can have many **Appointments**, **Admissions**, **Prescriptions**, and **Bills**; each child record belongs to one patient.
- One **Doctor** can attend many appointments and write many prescriptions.
- One **Room** can appear in historical admissions, but only one admission may be active in it at a time.
- One **Medicine** can be referenced by many prescriptions. Recording an instruction does not decrement inventory; stock changes only through the explicit stock-adjustment action.

All foreign keys use restrictive deletion behavior. The UI asks before deletion; Oracle rejects deletion where dependent records exist.

## 4. Relational schema and data dictionary

`NUMBER(10)` is used for generated identifiers and integer quantities; `NUMBER(10,2)` is used for prices and individual charges. The computed bill total uses `NUMBER(11,2)` so it can hold the sum of three maximum `NUMBER(10,2)` charges. `VARCHAR2` stores labels and contact/clinical text; `DATE` stores dates. IDs are Oracle identity columns (`GENERATED ALWAYS AS IDENTITY`), so hand-entered IDs are not needed.

| Table | Columns | Keys / rules |
|---|---|---|
| `Department` | `department_id NUMBER(10)`, `department_name VARCHAR2(100)`, `location VARCHAR2(150)` | PK `department_id`; unique, required department name; required location |
| `Doctor` | `doctor_id NUMBER(10)`, `doctor_name VARCHAR2(150)`, `specialization VARCHAR2(120)`, `phone VARCHAR2(20)`, `email VARCHAR2(254)`, `department_id NUMBER(10)` | PK; optional phone/email individually unique; required FK to Department |
| `Patient` | `patient_id NUMBER(10)`, `patient_name VARCHAR2(150)`, `date_of_birth DATE`, `gender CHAR(1)`, `phone VARCHAR2(20)`, `address VARCHAR2(300)`, `blood_group VARCHAR2(3)` | PK; optional phone unique; gender in `M`, `F`, `O`; nullable blood group in `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-` |
| `Appointment` | `appointment_id NUMBER(10)`, `patient_id NUMBER(10)`, `doctor_id NUMBER(10)`, `appointment_date DATE`, `appointment_time VARCHAR2(5)`, `status VARCHAR2(20)` | PK; FKs to Patient and Doctor; date is day-only; time is `HH:MM`; status in `Scheduled`, `Completed`, `Cancelled`; active-slot virtual columns enforce uniqueness |
| `Room` | `room_id NUMBER(10)`, `room_number VARCHAR2(20)`, `room_type VARCHAR2(40)`, `availability_status VARCHAR2(20)` | PK; unique required room number; state in `Available`, `Occupied`, `Maintenance` |
| `Admission` | `admission_id NUMBER(10)`, `patient_id NUMBER(10)`, `room_id NUMBER(10)`, `admission_date DATE`, `discharge_date DATE` | PK; FKs to Patient and Room; discharge cannot precede admission; virtual active keys enforce one active room and one active admission per patient |
| `Medicine` | `medicine_id NUMBER(10)`, `medicine_name VARCHAR2(150)`, `manufacturer VARCHAR2(150)`, `price NUMBER(10,2)`, `stock_quantity NUMBER(10)` | PK; nonnegative price and stock; defaults to zero |
| `Prescription` | `prescription_id NUMBER(10)`, `patient_id NUMBER(10)`, `doctor_id NUMBER(10)`, `medicine_id NUMBER(10)`, `dosage VARCHAR2(200)`, `duration VARCHAR2(100)`, `prescription_date DATE` | PK; FKs to Patient, Doctor, Medicine; dosage/duration required |
| `Bill` | `bill_id NUMBER(10)`, `patient_id NUMBER(10)`, `bill_date DATE`, `consultation_charge NUMBER(10,2)`, `room_charge NUMBER(10,2)`, `medicine_charge NUMBER(10,2)`, `total_amount NUMBER(11,2)`, `payment_status VARCHAR2(20)` | PK; FK to Patient; charges nonnegative; total is an Oracle virtual/computed column with precision for the sum of all three maximum charges; status in `Paid`, `Pending` |

### Key relationships

`Doctor.department_id → Department.department_id`; `Appointment.patient_id → Patient.patient_id`; `Appointment.doctor_id → Doctor.doctor_id`; `Admission.patient_id → Patient.patient_id`; `Admission.room_id → Room.room_id`; `Prescription.patient_id → Patient.patient_id`; `Prescription.doctor_id → Doctor.doctor_id`; `Prescription.medicine_id → Medicine.medicine_id`; `Bill.patient_id → Patient.patient_id`.

## 5. Integrity, concurrency, and design decisions

- Oracle `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `NOT NULL`, and `CHECK` rules are the authoritative integrity boundary. Backend validation improves the error message but is not relied on as the only guard.
- `Doctor.department_id` and transactional record foreign keys are `NOT NULL` so the web workflows cannot create unassigned doctors, visits, admissions, prescriptions, or bills.
- `Appointment` has virtual key columns populated only for `Scheduled` rows. Unique constraints therefore prevent two scheduled appointments for the same doctor/time and prevent a patient being double-booked at the same time. Cancelled/completed records remain history without reserving the slot. Oracle uniqueness is the final concurrency-safe guard. `TRG_APPOINTMENT_GUARD` also rejects scheduled visits dated before today and prevents edits to completed/cancelled history; the API/UI retain appointments rather than deleting them.
- `Admission` has virtual `active_room_id` and `active_patient_id` keys populated only when `discharge_date IS NULL`; unique constraints block duplicate active stays. A `BEFORE` trigger locks the room row and checks `Available`. An `AFTER` trigger marks a room `Occupied` on admission and `Available` on discharge. A third trigger prevents deleting an active admission before discharge. These effects participate in the same Oracle transaction. The API additionally locks a room before an availability edit.
- Bill `total_amount` is a virtual expression `consultation_charge + room_charge + medicine_charge`, rather than a caller-maintained value; it cannot diverge from its components. Charge columns default to zero and cannot be negative.
- Stock adjustment uses one conditional `UPDATE ... WHERE stock_quantity + :change >= 0`; Oracle row locking serializes concurrent updates and the table CHECK constraint remains the final lower-bound guard. Prescriptions intentionally do not consume inventory because there is no dispensing/fulfilment entity in the requested model.
- The schema uses `DATE` for appointments with the date portion constrained to midnight and a separate 24-hour `VARCHAR2(5)` time. This preserves the requested appointment date/time columns while making the unique slot key explicit.
- `ON DELETE CASCADE` is not used: patient/doctor/medicine/room/department history should not disappear implicitly. The API/UI also prohibit deleting appointment, admission, prescription, and bill history; only active admissions are additionally protected from direct SQL deletion by an Oracle trigger. The trigger guards that invariant, but the API-level rules retain all such history through the application.

### 3NF rationale

Each relation represents one entity or relationship record and has a generated single-column key. Descriptive attributes depend on that key, the whole key, and no other non-key attribute. Department names/locations appear only in Department; Doctor stores a department FK, not copied department details. Appointment stores patient/doctor FKs rather than copied names. Prescription stores FKs rather than patient/doctor/medicine descriptive details. Bills reference a patient and keep only bill-specific charge components. `total_amount` is a deterministic virtual calculation, not an independently maintained fact. This avoids transitive dependencies and update anomalies and meets the intended 3NF objective for the modeled scope.

## 6. SQL file purposes and run order

Run each file from the repository root using SQL*Plus/SQLcl and a new Oracle 12c+ schema:

```sql
@sql/01_create_schema.sql
@sql/02_sample_data.sql
@sql/03_useful_queries.sql
@sql/04_verification.sql
```

- `01_create_schema.sql`: creates tables in parent/dependency order, constraints, indexes through unique constraints, one appointment-state trigger, and three admission triggers (room guard, room synchronization, active-delete guard). It does not drop existing objects.
- `02_sample_data.sql`: fictional, relative-date examples in all nine tables; uses `NOT EXISTS` checks, updates no existing records, and commits at the end.
- `03_useful_queries.sql`: creates two report views and includes joined histories, doctor schedules, date/status counts, current admissions/history, room occupancy, prescription and inventory reports, bill detail/status/monthly revenue, aggregate and subquery examples. UPDATE/DELETE examples are comments for deliberate manual execution; appointment/admission/prescription/bill history is not deleted by the application.
- `04_verification.sql`: inspects columns, identity/virtual metadata, enabled constraints, foreign-key parent mappings, indexes, trigger/view status, and basic relationship counts.

The create script is intentionally for a fresh schema; a collision errors instead of dropping data. No destructive reset script is shipped.

## 7. Website configuration and API

Install and configure from the project root:

```sh
Linux/macOS:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python app.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Edit `.env` locally before launch; do not commit it. Set `ORACLE_USER`, `ORACLE_PASSWORD`, and `ORACLE_DSN` (for example `localhost:1521/FREEPDB1`), or set `ORACLE_HOST`, `ORACLE_PORT`, and `ORACLE_SERVICE_NAME`. The app uses a small connection pool and the python-oracledb Thin driver by default. Never publish the local password. Browse to <http://127.0.0.1:5000>.

Main routes:

- `GET /api/health`, `GET /api/dashboard`, `GET /api/options`
- `GET/POST /api/departments`, `/doctors`, `/patients`, `/appointments`, `/rooms`, `/admissions`, `/medicines`, `/prescriptions`, `/bills`
- `GET/PUT/DELETE /api/{resource}/{id}`
- `GET /api/patients/{id}/summary` for linked clinical and billing history; `GET /api/details/{resource}/{id}` for record details and related records
- `GET /api/reports/{report_name}` for one of twelve allowlisted, database-generated reports
- Collection list endpoints accept safe search/filter/sort and bounded `page`/`page_size` parameters and return pagination metadata
- `POST /api/medicines/{id}/stock-adjustments` with a signed integer `change`
- `POST /api/admissions/{id}/discharge` with `discharge_date`

The browser uses database-populated related-record dropdowns with type-to-filter, search/filter/sort/pagination, appointment table/agenda views, report filters, client/server validation, and inline feedback. Confirmation is required for state transitions and deletions. Appointment, admission, prescription, and bill history is retained through the application; no fake statistics/rows are bundled into the interface.

### Module-level feature matrix

| Module | Implemented UI/API features | Delete / history policy | Current verification evidence |
|---|---|---|---|
| Dashboard | Database counts, upcoming visits, pending bills, low stock, recent records, module links. | Read-only aggregates. | Fake-cursor API test and jsdom rendering with mocked payloads; Oracle unverified. |
| Departments | Create/edit, doctor counts/associations, search/sort/filter/page, details. | Delete allowed only if no doctor references. | General API/fake-query tests and jsdom module render; no live database test. |
| Doctors | Create/edit, department relation, filters/search/sort/page, appointment/prescription details. | Oracle FKs reject delete when history refers to doctor. | General API/fake-query tests and jsdom module render; no live database test. |
| Patients | Create/edit, blood group/gender filters, search/sort/page, joined four-part patient history. | FKs retain patient rows that have related history. | Fake API and jsdom patient-history smoke; no live database test. |
| Appointments | Book/reschedule, date/status filters, search/sort/page, agenda/table, complete/cancel, view. | Scheduled unique slots; no past scheduled visits; terminal history read-only; API/UI deletion disabled. | Fake API list/pagination test and jsdom agenda/status smoke. Oracle triggers/concurrency remain unverified. |
| Rooms | Create/edit, availability filter, search/sort/page, admission details. | Occupancy controlled by active admissions and database triggers. | API validation test and jsdom module render; live trigger behavior unverified. |
| Admissions | Admit, move an active stay to an available room, view active/discharged history, filter, and discharge/release room. | API only allows moving an active stay; no deletion or mutation of discharged history through app. | API deletion-policy fake test and jsdom module render; Oracle concurrency/triggers unverified. |
| Medicines | Create/edit, low-stock filter, search/sort/page, adjust stock, prescription details. | Stock adjustment is atomic; cannot underflow; dependent prescriptions protect deletion. | Fake API stock test and jsdom module render; Oracle atomicity unverified. |
| Prescriptions | Create/edit, patient/doctor/medicine relations, related/date filters, details. | Delete disabled to retain prescribing history. | API policy tests and jsdom module render; live FK/history behavior unverified. |
| Billing | Create/edit charges/status, filter/search/page, computed-total hint, detail/print. | Delete disabled to retain financial history; Oracle computes the total. | API validation and jsdom form/print smoke; computed-column behavior unverified. |
| Reports | Twelve joined, grouped, schedule, history, occupancy, inventory and revenue reports with filters/page controls. | Static query allowlist; no user-provided SQL identifiers. | Fake-cursor report/pagination tests and jsdom report selection; Oracle query execution unverified. |

**Status key:** the listed features are implemented in source and selectively exercised with fake database objects or mocked browser API responses. No row in this matrix implies live Oracle or real-browser end-to-end verification.

## 8. Testing and verification status

The default automated suite is `python -m unittest discover -s tests -v`; it uses fakes for backend behavior and skips the opt-in Oracle suite unless explicitly enabled. JavaScript syntax can be checked using `node --check static/app.js`. The live suite is `tests/test_oracle_integration.py` and uses the real `python-oracledb` driver and Oracle service—never SQLite or mocked Oracle.

**Automated/test-double evidence (2026-10-27):** `.venv/bin/python -m unittest discover -s tests -v` discovered 35 tests: 26 passed using fake database objects, three Oracle safety-guard unit tests passed, and six live-Oracle integration tests were skipped because opt-in was not enabled. `node --check static/app.js`, Python compilation, `git diff --check`, and a one-off `css-tree` parse (189 top-level rules) passed. A jsdom DOM/event smoke exercised the dashboard, all nine modules, all twelve reports, admission room move, appointment agenda/status, patient history, report pagination, bill details/print/form, related-select search, and reset using mocked API responses (45 requests). A separate no-Oracle HTTP startup check returned `/` 200 and structured `database_unavailable` 503 responses for `/api/health` and `/api/dashboard`. These checks do not test Oracle or visual layout in a real browser.

**Static-only review:** the SQL dependency order, nine-table/identity/FK model, virtual-column uniqueness rules, appointment/admission trigger flows, seed predicates, backend SQL/API fields, and frontend form/list fields were cross-checked. The schema declares nine tables, nine identity columns, nine foreign keys, one appointment-state trigger, and three admission triggers. The repeat-safe scheduled appointment seed statements check both doctor and patient active slot keys. `Patient.blood_group` is nullable but constrained to the eight standard groups. Bill `total_amount` is `NUMBER(11,2)` to accommodate three individual `NUMBER(10,2)` charges at their maximum values. This was a source review only; it does not establish that Oracle accepted the DDL or that the SQL behaves as intended at runtime.

| Evidence class | Result |
|---|---|
| **Real Oracle** | Not run. This workspace has no SQL*Plus/SQLcl executable, Oracle listener/process, `.env`, or configured `ORACLE_*` connection values; `/api/health` returns the expected structured HTTP 503. No DDL, seed, integration test, or live CRUD was run against Oracle. |
| **Automated / test doubles** | Latest Python suite: 35 discovered, 26 passed using fake database objects, three Oracle safety-guard unit tests passed, and six live-Oracle tests skipped. The prior jsdom smoke used mocked API responses and did not inspect visual layout. The no-Oracle HTTP smoke verified `/` 200 and health/dashboard 503 with structured errors. These checks verify application-side behavior only. |
| **Static-only** | The SQL/backend/frontend/documentation cross-check and changes described above; no Oracle parser/compiler or execution was available. |
| **Unverified** | Oracle 12c+ object/trigger compilation, seed insertion, actual check/unique/FK/virtual-column behavior, real concurrent transactions, Flask-to-Oracle CRUD, browser-to-Oracle flow, and visual layout in a real browser. The R1.pdf diagram artwork and team/contact allocation were not reproduced or compared; its extractable scope, table definitions, relationships, and 3NF objective were checked. |

### Dedicated disposable-schema procedure

Use the exact procedure in the README's [Dedicated Oracle integration-test schema](../README.md#dedicated-oracle-integration-test-schema) section: create a fresh `HMS_ORACLE_TEST` user in a non-production PDB with only the required schema privileges and tablespace quota; connect as that user; run `sql/01_create_schema.sql` through `sql/04_verification.sql` in order; configure `.env` with that exact user's local credentials; then set both `HMS_ORACLE_INTEGRATION=1` and `HMS_ORACLE_TEST_ACK=I_CONFIRM_HMS_ORACLE_TEST_IS_DISPOSABLE` before running `python -m unittest discover -s tests -p 'test_oracle_integration.py' -v`. The suite refuses to proceed unless the configured user, Oracle `SESSION_USER`, and `CURRENT_SCHEMA` all equal `HMS_ORACLE_TEST`, as well as requiring the acknowledgement. Never use a shared or production PDB. It creates uniquely named rows and cleans up only rows linked to tracked IDs; it never drops tables. If interrupted, inspect the test schema's `Oracle IT` and `IT-` rows before manual cleanup.

The live suite checks Oracle dictionary metadata and trigger validity, invalid rows against database constraints, computed bill totals, appointment slot conflicts/cancellation release (including concurrent inserts), admission room-status guards/moves/discharge, FK deletion restriction, and atomic stock adjustments. Execute `@sql/04_verification.sql` and review its output after the setup scripts, then retain the final command output as evidence.

## 9. Manual demonstration checklist

- [ ] Start Oracle and the Flask app; show the `Oracle connected` state.
- [ ] Open dashboard and point out counts, upcoming appointments, and pending balances from the database.
- [ ] Create a department; add a doctor with the database-populated department dropdown; filter the doctor list.
- [ ] Register a patient; search by name/phone and open the linked appointment/admission/prescription/bill history.
- [ ] Book appointments in distinct slots; attempt a conflicting slot and show the conflict response; switch to agenda view and complete/cancel a scheduled appointment while retaining its history.
- [ ] Add rooms; admit an existing patient; show the room becoming Occupied; move the active stay to another available room; discharge and show occupancy released.
- [ ] Add a medicine; adjust stock; try to remove more than the current balance and show the guard.
- [ ] Create a prescription and explain that stock is not decremented absent a dispense record.
- [ ] Generate a bill; show its computed total, update payment status, open bill details, and use Print bill.
- [ ] Choose joined/history, occupancy, low-stock, and monthly-revenue reports; try a report filter and page controls.
- [ ] Attempt to delete a referenced master record; show safe rejection. Confirm appointment, admission, prescription, and bill history cannot be deleted through the app.
- [ ] Resize to a narrow viewport and test keyboard focus, form labels, modal Escape, and the confirmation dialog.

## 10. Limitations and future improvements

- Oracle execution and UI end-to-end behavior must be validated in the target lab environment; Oracle is not installed in this workspace.
- No authentication/authorization is implemented; run only on a trusted local network with a least-privilege Oracle account.
- Stock changes have no append-only transaction/dispensing history. A future version should add a Dispense/StockMovement table before relating prescriptions to fulfilment.
- Appointment availability does not model clinic opening hours, doctor leave, appointment duration, or overlapping durations beyond an exact slot.
- Billing has no insurance, taxes, invoice line items, receipts, or payment gateway.
- Audit logging, backup/restore guidance, deployment configuration, accessibility testing with assistive technologies, and clinical privacy controls remain future work. The app is not production-hardened.
