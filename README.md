# Hospital Management System — BCSE302P

A college Database Systems project built around an Oracle relational database, a small Flask service, and a responsive HTML/CSS/JavaScript interface. The repository initially contained only a placeholder README. The 13-page source report (`R1.pdf`) was supplied for the pre-publication audit; its extractable nine-table scope, key relationships, and 3NF objective were checked against the implementation. This implementation retains the nine entities and adds more detailed constraints and application workflows. The source report's diagram artwork and team/contact details are not reproduced here.

## Architecture

- **Database:** Oracle Database 12c or later; identity columns, check/unique/foreign-key constraints, virtual columns, admission-room triggers, and an appointment-state trigger.
- **Backend:** Python 3.10+, Flask, official `python-oracledb` driver in Thin mode by default. Credentials are read from environment variables / a local `.env` file.
- **Frontend:** semantic HTML, responsive CSS, and browser JavaScript served by Flask. Browser code calls only relative `/api/...` endpoints; it never connects to Oracle.
- **Data flow:** browser → Flask JSON API → parameterized Oracle SQL. Mutations commit on success and roll back on error.

The nine relations are **Department, Doctor, Patient, Appointment, Room, Admission, Medicine, Prescription,** and **Bill**. Foreign keys use Oracle's default `NO ACTION`/restrict behavior: records with dependent history cannot be deleted by accident.

## Frontend design direction

The product-specific hierarchy, visual tokens, compliance review, and verification limits are documented in [`docs/FRONTEND_DESIGN.md`](docs/FRONTEND_DESIGN.md). The full supplied acceptance playbook is preserved at [`docs/FrontEnd.md`](docs/FrontEnd.md).

The interface is an educational **hospital administration/operations** app, not a patient portal, clinical decision tool, or live hospital service. Its visual hierarchy prioritizes the records staff need to act on—today's appointment queue and upcoming visits, active admissions, available rooms, and pending bills—then presents register and payment totals as supporting context. Every figure is rendered from the existing dashboard API response; an unavailable database produces an error state, not sample KPI values, trend claims, or assumed identities.

The UI uses a restrained navy/teal system, the platform's system font, stronger text/control contrast, and shared 12/13/14px text tokens. Dense records stay in semantic tables; narrow screens can scroll each table in a labeled, keyboard-focusable region rather than silently dropping columns. The appointment agenda reflows at small widths, and the dated queue labels its booked-time ordering while explicitly noting that arrival order and triage priority are not recorded. Desktop navigation remains persistent; mobile navigation is an overlay with a backdrop, Escape handling, focus return/trapping, and an inert closed drawer. Focus rings and reduced-motion preferences are supported in CSS.

These are implemented design decisions, not a completed accessibility certification or visual QA sign-off. Browser-specific rendering and assistive-technology behavior still need review in a real browser/device setup; see the verification boundary below.

## Repository map

```text
sql/01_create_schema.sql      Non-destructive schema and integrity triggers
sql/02_sample_data.sql       Fictional, repeat-safe demo rows
sql/03_useful_queries.sql    Views, reports, and commented DML examples
sql/04_verification.sql     Dictionary/constraint/relationship checks
hms/                         Flask API, Oracle connection pool, validation
static/                      HTML, CSS, and JavaScript UI
tests/                       Test-double checks plus opt-in live Oracle integration tests
docs/PROJECT_REPORT.md       Submission-oriented technical report
docs/FRONTEND_DESIGN.md      Frontend direction, compliance, and verification limits
docs/FrontEnd.md             Full supplied frontend acceptance playbook
docs/ER_DIAGRAM.mmd          Editable Mermaid ER diagram
.env.example                 Safe configuration template
```

## Oracle setup

Use an Oracle 12c+ schema/user with permission to create tables, views, and triggers and sufficient tablespace quota. Identity sequences and constraint indexes are managed by Oracle. Run the website with a schema that can read and write these project tables. Do not use a production account. Configure the database account locally; do not put its password in source control.

1. Connect to the target Oracle service with SQL*Plus or SQLcl:

   ```sh
   sqlplus hms_app@//localhost:1521/FREEPDB1
   ```

   SQL*Plus prompts for the password. The Easy Connect service name is an example; substitute your database's host, port, and service name.

2. At the SQL prompt, run the scripts in order:

   ```sql
   @sql/01_create_schema.sql
   @sql/02_sample_data.sql
   @sql/03_useful_queries.sql
   @sql/04_verification.sql
   ```

   `01_create_schema.sql` intentionally does **not** drop or replace tables. It is for a new schema and will fail rather than destroy an existing schema. This four-script setup is not an in-place migration: earlier project schemas have a smaller appointment-status constraint/slot rule, and no upgrade migration is shipped. Do not point the updated app at an older schema; use a fresh project schema or obtain and review a safe migration first. `02_sample_data.sql` uses fictional records and `NOT EXISTS` checks so rerunning it on the same day does not add duplicate demo rows. It does not delete existing data. Queries in script 03 include report views and read-only examples; its UPDATE/DELETE examples are commented until deliberately run with a chosen key.

3. You can also run a single script from a shell (the password is prompted for, not embedded in the command):

   ```sh
   sqlplus hms_app@//localhost:1521/FREEPDB1 @sql/01_create_schema.sql
   ```

   Repeat with the remaining script names. SQL*Plus and a reachable Oracle service are required; they are not included in this repository.

There is no automatic reset script. If a clean database is required, use a newly created disposable Oracle schema rather than dropping project tables.

## Dedicated Oracle integration-test schema

The live integration suite is opt-in and must use a **fresh, disposable schema** in a non-production Oracle PDB. It creates only uniquely named synthetic rows and cleans up the rows it created; it never drops tables or truncates data. Use a test-only database account, never an application or production account. The suite refuses to connect unless `ORACLE_USER`, Oracle `SESSION_USER`, and `CURRENT_SCHEMA` are all exactly `HMS_ORACLE_TEST`, and it also requires a separate explicit disposable-schema acknowledgement.

1. As a local PDB administrator (not the app user), create a new schema. Replace the password and tablespace names locally; `USERS`/`TEMP` are examples and vary by Oracle installation:

   ```sql
   CREATE USER HMS_ORACLE_TEST IDENTIFIED BY "replace-with-a-random-local-secret"
     DEFAULT TABLESPACE users
     TEMPORARY TABLESPACE temp
     QUOTA 100M ON users;
   GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE TRIGGER TO HMS_ORACLE_TEST;
   ```

2. Connect as `HMS_ORACLE_TEST` to the chosen non-production PDB and run all four setup scripts, in order, from the repository root:

   ```sql
   @sql/01_create_schema.sql
   @sql/02_sample_data.sql
   @sql/03_useful_queries.sql
   @sql/04_verification.sql
   ```

   Review the verification output and confirm the schema objects are enabled before running tests. Do not point this procedure at a shared or production schema.

3. Set `.env` to the test-only account (`ORACLE_USER=HMS_ORACLE_TEST`, its local password, and that non-production PDB's DSN). Then explicitly opt in and acknowledge the disposable schema.

   Linux/macOS:

   ```sh
   export HMS_ORACLE_INTEGRATION=1
   export HMS_ORACLE_TEST_ACK=I_CONFIRM_HMS_ORACLE_TEST_IS_DISPOSABLE
   python -m unittest discover -s tests -p 'test_oracle_integration.py' -v
   ```

   Windows PowerShell:

   ```powershell
   $env:HMS_ORACLE_INTEGRATION = "1"
   $env:HMS_ORACLE_TEST_ACK = "I_CONFIRM_HMS_ORACLE_TEST_IS_DISPOSABLE"
   python -m unittest discover -s tests -p 'test_oracle_integration.py' -v
   ```

   The tests use the actual `python-oracledb` driver and Oracle database, not SQLite or an Oracle mock. Before writing, the suite requires the configured user, Oracle `SESSION_USER`, and `CURRENT_SCHEMA` to equal `HMS_ORACLE_TEST`; the acknowledgement is also mandatory. It checks schema metadata, constraints, generated bill totals, appointment-slot uniqueness (including two concurrent sessions), admission/room triggers, deletion restrictions, and atomic stock changes. Setup/teardown deletes only synthetic rows linked to IDs created by each test instance. If a run is interrupted, inspect uniquely named `Oracle IT` / `IT-...` rows in the dedicated test schema before manually cleaning them; the suite never drops schema objects. Do not run these commands against any shared or production PDB.

## Configure and launch the website

From the repository root, use the commands for your shell.

Linux/macOS:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` locally. Set `ORACLE_USER`, `ORACLE_PASSWORD`, and either `ORACLE_DSN` or `ORACLE_HOST`, `ORACLE_PORT`, and `ORACLE_SERVICE_NAME`. The example uses the Oracle Free PDB service `FREEPDB1`; use the actual service name provided by your Oracle installation. `python-oracledb` uses Thin mode by default, so Oracle Instant Client is not needed for a standard TCP Oracle connection.

Start the app:

```sh
python app.py
```

Open <http://127.0.0.1:5000>. Set `PORT` to change the port. `FLASK_DEBUG=true` enables the development reloader and should only be used locally. The dashboard and modules read live database data; with no configured/reachable Oracle database, the interface displays a connection error rather than fabricated statistics.

## Module feature matrix

| Area | Implemented workflow | Integrity / history rules |
|---|---|---|
| Dashboard | Oracle-backed counts including today's active appointment queue, upcoming appointments, outstanding bills, low-stock medicines, recent dated records, module links, and an explicit refresh action. | No demo/fabricated statistics; a disconnected database shows an error state. |
| Departments | Create, edit, search, sort, paginate, inspect associated doctors, and delete only when unreferenced. | Unique department name; doctor foreign keys prevent destructive parent deletion. |
| Doctors | Create/edit profiles, choose a department, search/filter/sort/page, inspect appointments and prescriptions, and delete only when unreferenced. | Required department FK; phone/email validation and optional unique values. |
| Patients | Register/edit, search/filter by gender/blood group, sort/page, and review a newest-first chart that merges appointments, admissions/discharges, prescription instructions, and bills; print the chart. | Date/phone/blood-group validation; dependent foreign keys protect history. The chart labels stored administrative facts only and disclaims diagnosis, triage, and dispensing records. |
| Appointments | Book/reschedule scheduled visits; search/filter/date-range/sort/page; table, date-grouped agenda, or dated/doctor-filtered queue; check in, wait, begin/complete a consultation, cancel, or mark an overdue visit No-show. | Doctor and patient slot uniqueness across all active states; only Scheduled visits may be rescheduled; check-in is limited to the appointment date and No-show to a past date; terminal records are read-only and cannot be deleted through the app. |
| Rooms | Create/edit room details; search/filter/sort/page and inspect admissions. | Availability is synchronized with admission; manual Occupied state is disallowed. |
| Admissions | Admit to an available room, move an active stay to another available room, review stay history, discharge/release, and search/filter/date-range/sort/page. | One active admission per patient/room; room moves/discharge update occupancy transactionally; history is retained through the app. |
| Medicines | Create/edit catalogue, search/filter low stock/sort/page, inspect prescriptions, and add/remove stock. | Nonnegative stock; atomic stock adjustment; direct stock editing is rejected; manual adjustments are not dispense records and prescriptions do not consume stock. |
| Prescriptions | Create/edit instructions with patient/doctor/medicine relations; search/filter by related record/date and page; inspect details. | Required foreign keys and bounded fields; prescription history cannot be deleted through the app. |
| Billing | Create/edit charge components and payment status; search/filter patient/status/date, page, inspect and print a bill. | Oracle-computed total; nonnegative charges; paid/pending bill history cannot be deleted through the app. |
| Reports | Twelve database queries for joins, appointments/schedules, admission history/current occupancy, inventory, prescriptions, bills, monthly revenue, and grouped summaries; filter and paginate; export every row matching current filters to CSV. | Static, parameterized query definitions; CSV neutralizes formula-prefixed text; export is independent of the visible page; totals mean bills marked Paid/Pending, not gateway settlements. |
| Shared UX | Related-record dropdowns with type-to-filter, required-field checks, reset, inline errors/toasts, confirmations, modal Escape/focus handling, responsive CSS, print-ready patient/bill records, and safe HTML escaping. | All browser calls use same-origin Flask endpoints; no Oracle credentials or SQL in browser code. |

**Verification boundary:** this matrix describes implemented source behavior. Fake-Oracle tests exercise backend request/query construction and jsdom exercises rendered DOM/event behavior with mocked API payloads. They do not verify Oracle execution, concurrency, visual layout in a real browser, or a live end-to-end workflow.

## Verification and tests

Run the automated tests and JavaScript syntax check (activate `.venv` first):

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

**Latest implementation checks (2026-10-27):** `.venv/bin/python -m unittest discover -s tests -v` ran 45 tests: 38 passed (35 fake-database/API/validation/helper tests and three Oracle safety-guard unit tests); seven opt-in live-Oracle integration tests were skipped. Python compilation, `node --check static/app.js`, CSS parsing/custom-property checks, HTML parsing/duplicate-ID checks, and `git diff --check` passed. A temporary jsdom interaction smoke made 79 mocked API calls and exercised the dashboard and unavailable state, all nine modules, all twelve reports, related-record selectors, search/sorting/pagination, a mocked create payload, appointment table/agenda/queue modes and lifecycle actions, the patient timeline and print action, filtered CSV download, and mobile-drawer state at 390px/1024px. This is DOM/event verification, not browser rendering or an Oracle-backed workflow. Selected source-color measurements reported 4.65:1 for sidebar normal text and 3.52:1 for input borders; these are not a complete WCAG audit. A Flask test-client check confirmed `/` and static assets are served, while `/api/health` and `/api/dashboard` return structured HTTP 503 `database_unavailable` responses without Oracle configuration. No live Oracle instance or real browser was available; DDL execution, rendered screenshots, real-device/zoom/reflow, assistive-technology behavior, browser console/network inspection, and live CRUD/workflows remain unverified.

**Real-Oracle integration:** after preparing the dedicated schema above, run the opt-in suite with `HMS_ORACLE_INTEGRATION=1`. Do not count skipped tests as Oracle verification. Run `@sql/04_verification.sql` after schema/data setup and review its output.

### Audit evidence for this workspace

| Evidence class | Result |
|---|---|
| **Real Oracle** | **Not run / unverified.** No Oracle credentials, `.env`, SQL*Plus/SQLcl, or local Oracle listener were available in this workspace. No SQL file or integration test was executed against Oracle. A Flask test-client check without database configuration returned the expected structured HTTP 503, which is not live-database evidence. |
| **Automated / test doubles** | Latest unittest run: 45 tests, comprising 35 fake-database/API/validation/helper passes, three Oracle safety-guard unit-test passes, and seven skipped live-Oracle tests. The temporary jsdom smoke used mocked API responses (79 calls); responsive checks observed DOM state only. These do not verify live Oracle or real-browser layout. |
| **Static-only** | Reviewed the SQL, API, frontend field definitions, tests, README, report, and ER diagram. The static model has nine tables, nine identity columns, nine foreign keys, one appointment-state trigger, and three admission triggers; conditional unique keys protect appointment slots in all active workflow states and active admissions. Seed statements were checked for dependency order and slot-conflict guards; no Oracle parser or compiler was available. |
| **Unverified** | Oracle 12c+ DDL/trigger compilation, seed execution, constraint/virtual-column behavior, actual concurrent sessions, live Flask-to-Oracle CRUD, browser-to-Oracle flows, and real-browser visual layout. The extractable scope/schema/relationship text in `R1.pdf` was compared; its diagram artwork and team/contact allocation were not reproduced or compared. |

For the exact Oracle test procedure and manual verification checklist, see [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md) and the dedicated schema instructions above.

## Project documentation

See [`docs/PROJECT_REPORT.md`](docs/PROJECT_REPORT.md) for the data dictionary, key relationships, 3NF rationale, integrity rules, testing limitations, and manual demonstration checklist. The Mermaid source of the implemented ER model is [`docs/ER_DIAGRAM.mmd`](docs/ER_DIAGRAM.mmd).
