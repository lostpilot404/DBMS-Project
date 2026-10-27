# Hospital Management System

**Course:** BCSE302P — Database Systems<br>
**Database:** Oracle Database 12c+<br>
**Interface:** HTML5, CSS3, JavaScript<br>
**Backend:** Python 3 / Flask / `python-oracledb`

> **Requirements-source note:** The 13-page source report (`R1.pdf`) was not available during initial implementation but was supplied for the pre-publication audit. Its extractable scope, nine table definitions, key relationships, and 3NF objective were compared against the implementation. The nine-entity model aligns; this implementation refines several data-type sizes and adds application and integrity safeguards. The report's diagram artwork and team/contact details are not reproduced or evaluated in this report.

## 1. Overview and scope

This project demonstrates a relational hospital information system for departments, doctors, patients, appointments, rooms, admissions, medicines, prescriptions, and patient bills. It includes a nine-table Oracle schema, integrity constraints, illustrative fictional records, twelve reporting queries, a JSON API, and a responsive browser interface. The application workflows include a constrained appointment queue/lifecycle, a unified printable patient history, and filtered CSV report exports without adding a tenth entity.

The application is an educational project, not a clinical or financial production system. It does not provide authentication, role-based access, audit history, electronic prescribing safeguards, payment processing, or a dispensing ledger. These limits are shown in the UI where relevant; no login, triage, diagnosis, or medication fulfilment is implied.

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
| `Appointment` | `appointment_id NUMBER(10)`, `patient_id NUMBER(10)`, `doctor_id NUMBER(10)`, `appointment_date DATE`, `appointment_time VARCHAR2(5)`, `status VARCHAR2(20)` | PK; FKs to Patient and Doctor; date is day-only; time is `HH:MM`; status is `Scheduled`, `Checked In`, `Waiting`, `In Consultation`, `Completed`, `Cancelled`, or `No-show`; virtual active-slot columns enforce doctor/patient uniqueness throughout an in-progress visit |
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
- `Appointment` has virtual key columns populated for `Scheduled`, `Checked In`, `Waiting`, and `In Consultation` rows. Unique constraints therefore prevent two active visits from reserving the same doctor/time or patient/time; terminal `Completed`, `Cancelled`, and `No-show` history releases the slot. Oracle uniqueness is the final concurrency-safe guard. `TRG_APPOINTMENT_GUARD` requires new rows to start as Scheduled, rejects scheduled visits dated before today, allows only `Scheduled → Checked In → Waiting → In Consultation → Completed`, plus `Scheduled → Cancelled` and `Scheduled → No-show`, limits check-in to the appointment date and No-show to dates in the past, and makes terminal records read-only. Rescheduling is allowed only while Scheduled; the API locks the row and applies matching validation. Appointments are retained rather than deleted.
- `Admission` has virtual `active_room_id` and `active_patient_id` keys populated only when `discharge_date IS NULL`; unique constraints block duplicate active stays. A `BEFORE` trigger locks the room row and checks `Available`. An `AFTER` trigger marks a room `Occupied` on admission and `Available` on discharge. A third trigger prevents deleting an active admission before discharge. These effects participate in the same Oracle transaction. The API additionally locks a room before an availability edit.
- Bill `total_amount` is a virtual expression `consultation_charge + room_charge + medicine_charge`, rather than a caller-maintained value; it cannot diverge from its components. Charge columns default to zero and cannot be negative.
- Manual medicine stock adjustment uses one conditional `UPDATE ... WHERE stock_quantity + :change >= 0`; Oracle row locking serializes concurrent adjustments and the table CHECK constraint remains the final lower-bound guard. These adjustments are not dispensing records and do not identify a prescription, quantity dispensed, or operator. Prescription creation intentionally does not consume inventory because the nine-entity assignment model has no dispensing/fulfilment or stock-movement relation.
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
- `02_sample_data.sql`: fictional, relative-date examples in all nine tables; uses `NOT EXISTS` checks, limits appointment lifecycle updates to the identity just inserted by that run, lets admission triggers synchronize room state, and commits at the end.
- `03_useful_queries.sql`: creates two report views and includes joined histories, doctor schedules, date/status counts, current admissions/history, room occupancy, prescription and inventory reports, bill detail/status/monthly revenue, aggregate and subquery examples. UPDATE/DELETE examples are comments for deliberate manual execution; appointment/admission/prescription/bill history is not deleted by the application.
- `04_verification.sql`: inspects columns, identity/virtual metadata, enabled constraints, foreign-key parent mappings, indexes, trigger/view status, and basic relationship counts.

The create script is intentionally for a fresh schema; a collision errors instead of dropping data. This script set is not an in-place migration for earlier project schemas: appointment-status/active-slot rules changed, and no upgrade migration is shipped. Do not connect the updated application to an older schema until a safe migration has been separately reviewed. No destructive reset script is shipped.

## 7. Website configuration and API

Install and configure from the project root.

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
- `GET /api/patients/{id}/summary` for linked patient facts and a newest-first timeline of appointments, admissions/discharges, prescription instructions, and bills; `GET /api/details/{resource}/{id}` for record details and related records
- `GET /api/appointments/queue?date=YYYY-MM-DD[&doctor_id=…]` for a database-backed day's status counts and deterministic booked-time queue; it does not claim arrival order or triage priority
- `GET /api/reports/{report_name}` for one of twelve allowlisted, database-generated reports; `GET /api/reports/{report_name}/csv` exports every row matching the validated report filters, independent of the visible page
- Collection list endpoints accept safe search/filter/sort and bounded `page`/`page_size` parameters and return pagination metadata
- `POST /api/medicines/{id}/stock-adjustments` with a signed integer `change` (manual stock adjustment only, not a prescription dispense record)
- `POST /api/admissions/{id}/discharge` with `discharge_date`

The browser uses database-populated related-record dropdowns with type-to-filter, search/filter/sort/pagination, appointment table/agenda/queue views, report filters and CSV export, a printable patient chart and bill details, client/server validation, and inline feedback. Confirmation is required for state transitions and deletions. Appointment, admission, prescription, and bill history is retained through the application; no fake statistics/rows are bundled into the interface.

### Module-level feature matrix

| Module | Implemented UI/API features | Delete / history policy | Current verification evidence |
|---|---|---|---|
| Dashboard | Database counts, upcoming visits, pending bills, low stock, recent records, module links. | Read-only aggregates. | Fake-cursor API test and jsdom rendering with mocked payloads; Oracle unverified. |
| Departments | Create/edit, doctor counts/associations, search/sort/filter/page, details. | Delete allowed only if no doctor references. | General API/fake-query tests and jsdom module render; no live database test. |
| Doctors | Create/edit, department relation, filters/search/sort/page, appointment/prescription details. | Oracle FKs reject delete when history refers to doctor. | General API/fake-query tests and jsdom module render; no live database test. |
| Patients | Create/edit, blood group/gender filters, search/sort/page; newest-first unified timeline for appointments, admissions/discharges, prescriptions, and bills; print patient record. | FKs retain patient rows that have related history. The chart does not assert diagnosis, triage, or dispensing facts. | Fake API summary/timeline test and jsdom chart/print interaction with mocked data; no live database or print-layout test. |
| Appointments | Book/reschedule; date/status filters, search/sort/page; table, agenda, or daily queue filtered by date/doctor; check-in, waiting, consultation, completion, cancel, and overdue No-show transitions. | Active statuses reserve unique slots; only Scheduled visits can be rescheduled; check-in is scheduled-day only, No-show requires a past date; terminal history is read-only and API/UI deletion is disabled. | Fake API workflow/queue/date-rule tests and jsdom mode/filter/transition smoke. Oracle trigger and concurrency behavior remain unverified. |
| Rooms | Create/edit, availability filter, search/sort/page, admission details. | Occupancy controlled by active admissions and database triggers. | API validation test and jsdom module render; live trigger behavior unverified. |
| Admissions | Admit, move an active stay to an available room, view active/discharged history, filter, and discharge/release room. | API only allows moving an active stay; no deletion or mutation of discharged history through app. | API deletion-policy fake test and jsdom module render; Oracle concurrency/triggers unverified. |
| Medicines | Create/edit, low-stock filter, search/sort/page, manual atomic stock adjustment, prescription details. | Adjustments cannot underflow; dependent prescriptions protect deletion. There is no dispense record or append-only stock ledger, and prescription creation never changes stock. | Fake API stock tests and jsdom module render; Oracle atomicity unverified. |
| Prescriptions | Create/edit, patient/doctor/medicine relations, related/date filters, details. | Delete disabled to retain prescribing history; a prescription is an instruction, not proof of dispensing. | API policy tests and jsdom module render; live FK/history behavior unverified. |
| Billing | Create/edit charges/status, filter/search/page, computed-total hint, detail/print. | Delete disabled to retain financial history; Oracle computes the total. | API validation and jsdom form/print smoke; computed-column behavior unverified. |
| Reports | Twelve joined, grouped, schedule, history, occupancy, inventory and revenue reports with filters/page controls and full filtered CSV export. | Static query allowlist; no user-provided SQL identifiers; export uses validated filters and neutralizes formula-prefixed text. | Fake-cursor query/pagination/CSV tests and jsdom filter/download smoke; Oracle query execution unverified. |

**Status key:** the listed features are implemented in source and selectively exercised with fake database objects or mocked browser API responses. No row in this matrix implies live Oracle or real-browser end-to-end verification.

## 8. Testing and verification status

The default automated suite is `python -m unittest discover -s tests -v`; it uses fakes for backend behavior and skips the opt-in Oracle suite unless explicitly enabled. JavaScript syntax can be checked using `node --check static/app.js`. The live suite is `tests/test_oracle_integration.py` and uses the real `python-oracledb` driver and Oracle service—never SQLite or mocked Oracle.

**Automated/test-double evidence (2026-10-27):** `.venv/bin/python -m unittest discover -s tests -v` ran 45 tests: 38 passed (35 fake-database/API/validation/helper tests plus three Oracle safety-guard unit tests) and seven live-Oracle integration tests were skipped because opt-in was not enabled. Python compilation, `node --check static/app.js`, CSS parsing/custom-property checks, HTML parsing/duplicate-ID checks, and `git diff --check` passed. A temporary jsdom DOM/event smoke made 79 mocked API calls and covered the dashboard/unavailable state, all nine modules, all twelve reports, related-record selectors, search/sorting/pagination, appointment table/agenda/queue modes and lifecycle transitions, the unified patient timeline and print action, and filtered CSV download. It did not render pixels or use Oracle. A Flask test-client check without database configuration served `/` and static assets and returned structured `database_unavailable` HTTP 503 responses for `/api/health` and `/api/dashboard`. These checks do not establish Oracle execution, real-browser appearance, or physical printing behavior.

**Static-only review:** the SQL dependency order, nine-table/identity/FK model, virtual-column uniqueness rules, appointment/admission trigger flows, seed predicates, backend SQL/API fields, and frontend form/list fields were cross-checked. The schema declares nine tables, nine identity columns, nine foreign keys, one appointment-state trigger, and three admission triggers. The repeat-safe appointment seeds guard active doctor slots and avoid reusing a patient's existing slot; the completed/cancelled examples update only rows they have just inserted. `Patient.blood_group` is nullable but constrained to the eight standard groups. Bill `total_amount` is `NUMBER(11,2)` to accommodate three individual `NUMBER(10,2)` charges at their maximum values. This was a source review only; it does not establish that Oracle accepted the DDL or that the SQL behaves as intended at runtime.

| Evidence class | Result |
|---|---|
| **Real Oracle** | Not run. No Oracle credentials, `.env`, SQL*Plus/SQLcl executable, or Oracle service were configured in this workspace. No DDL, seed, integration test, or live CRUD was run against Oracle. |
| **Automated / test doubles** | Latest Python suite: 45 tests, with 35 fake-database/API/validation/helper passes, three Oracle safety-guard passes, and seven skipped live-Oracle tests. The jsdom smoke used mocked API responses (79 calls), with DOM-state assertions only. Flask test-client checks confirmed static responses and structured no-database errors. These verify application-side behavior only. |
| **Static-only** | The SQL/backend/frontend/documentation cross-check and current source checks; no Oracle parser/compiler or execution was available. The schema declares nine tables, nine identity columns, nine foreign keys, one appointment-state trigger, and three admission triggers; virtual active keys cover every in-progress appointment state. |
| **Unverified** | Oracle 12c+ object/trigger compilation, seed insertion, actual check/unique/FK/virtual-column behavior, real concurrent transactions, Flask-to-Oracle CRUD, browser-to-Oracle flow, and visual/print layout in a real browser. The `R1.pdf` diagram artwork and team/contact allocation were not reproduced or compared; its extractable scope, table definitions, relationships, and 3NF objective were checked. |

### Dedicated disposable-schema procedure

Use the exact procedure in the README's [Dedicated Oracle integration-test schema](../README.md#dedicated-oracle-integration-test-schema) section: create a fresh `HMS_ORACLE_TEST` user in a non-production PDB with only the required schema privileges and tablespace quota; connect as that user; run `sql/01_create_schema.sql` through `sql/04_verification.sql` in order; configure `.env` with that exact user's local credentials; then set both `HMS_ORACLE_INTEGRATION=1` and `HMS_ORACLE_TEST_ACK=I_CONFIRM_HMS_ORACLE_TEST_IS_DISPOSABLE` before running `python -m unittest discover -s tests -p 'test_oracle_integration.py' -v`. The suite refuses to proceed unless the configured user, Oracle `SESSION_USER`, and `CURRENT_SCHEMA` all equal `HMS_ORACLE_TEST`, as well as requiring the acknowledgement. Never use a shared or production PDB. It creates uniquely named rows and cleans up only rows linked to tracked IDs; it never drops tables. If interrupted, inspect the test schema's `Oracle IT` and `IT-` rows before manual cleanup.

The live suite checks Oracle dictionary metadata and trigger validity, invalid rows against database constraints, computed bill totals, appointment slot conflicts/cancellation release (including concurrent inserts), admission room-status guards/moves/discharge, FK deletion restriction, and atomic stock adjustments. Execute `@sql/04_verification.sql` and review its output after the setup scripts, then retain the final command output as evidence.

## 9. Manual demonstration checklist

- [ ] Start Oracle and the Flask app; show the `Oracle connected` state.
- [ ] Open dashboard and point out counts, upcoming appointments, and pending balances from the database.
- [ ] Create a department; add a doctor with the database-populated department dropdown; filter the doctor list.
- [ ] Register a patient; search by name/phone, open the newest-first timeline across appointment, admission/discharge, prescription, and bill records, and use Print patient record. Point out the explicit limitation that diagnosis, triage, and dispensing are not in the chart.
- [ ] Book appointments in distinct slots; attempt a conflicting slot and show the conflict response; open the date/doctor queue and agenda; demonstrate Scheduled → Checked In → Waiting → In Consultation → Completed, then cancel another scheduled visit while retaining history. Explain that queue order follows booked time within status, not arrival or triage priority; a No-show requires a past appointment date.
- [ ] Add rooms; admit an existing patient; show the room becoming Occupied; move the active stay to another available room; discharge and show occupancy released.
- [ ] Add a medicine; adjust stock; try to remove more than the current balance and show the guard.
- [ ] Create a prescription and explain that stock is not decremented absent a dispense record.
- [ ] Generate a bill; show its computed total, update payment status, open bill details, and use Print bill.
- [ ] Choose joined/history, occupancy, low-stock, and monthly-revenue reports; try a filter and page controls; export CSV and confirm it reflects current filters, not just the visible page.
- [ ] Attempt to delete a referenced master record; show safe rejection. Confirm appointment, admission, prescription, and bill history cannot be deleted through the app.
- [ ] Resize to a narrow viewport and test keyboard focus, form labels, modal Escape, and the confirmation dialog.

## 10. Limitations and future improvements

- Oracle DDL/data execution and a real browser-to-Oracle workflow still require verification in the target lab environment; no live Oracle service was available for this audit.
- No authentication or authorization is implemented. A superficial login was not added because the project has no identity/role model; run only in a controlled local environment with a least-privilege Oracle account and do not use real patient data.
- Prescription dispensing is deliberately out of scope for this nine-entity model. Manual stock adjustments are atomic and prevent a negative balance but are not dispensing records, are not linked to prescriptions, and have no append-only stock history. A dispensing feature would need assignment approval and a complete schema/API/UI/verification extension (including a dispense or stock-movement relation), not a label change or shortcut.
- Appointment availability does not model clinic opening hours, doctor leave, appointment duration, or overlapping durations beyond an exact slot. Queue priority is based on status and booked time; arrival order, triage, and clinical priority are not recorded.
- Billing has no insurance, taxes, invoice line items, receipts, or payment gateway.
- Audit logging, backup/restore guidance, deployment configuration, accessibility testing with assistive technologies, and clinical privacy controls remain future work. The app is not production-hardened.
