# Hospital Management System — BCSE302P

An **academic, synthetic-data demonstration** using Oracle 12c+, Flask and plain JavaScript. Not a clinical system, payment processor, or production/real-patient-data service.

## Current status — 2026-10-29

Release verification and Git provenance: [canonical release assessment](docs/REPAIR_CAMPAIGN.md#final-release--2026-10-29). Teacher rehearsal: [guide §10](docs/MULTIUSER_GUIDE.md#10-teacher-rehearsal-without-oracle--explicit-test-fixture-only). Readiness is **Demonstration-ready with stated limitations**, not Oracle-certified.

The H01–H15 repair implementation spans database guards/migration, API, frontend, invoice printing, histories and documentation. **Live Oracle certification remains blocked:** no Oracle service/credentials are available here. Do not confuse Python test doubles or browser fixtures with persisted Oracle workflows. See [campaign results and remaining blockers](docs/REPAIR_CAMPAIGN.md), [manual matrix](docs/MANUAL_TEST_MATRIX.md), and [execution checklist](docs/superpowers/plans/2026-10-29-hms-repair.md).

**Multi-user extension:** personal database-backed accounts and nine role workspaces are implemented, with connected outpatient and inpatient flows. Default authentication is ON; there are no default production credentials. See the [setup / roles / workflow guide](docs/MULTIUSER_GUIDE.md) and [tested / partial / blocked status matrix](docs/REPAIR_CAMPAIGN.md). This is not “complete because login works”: retained amendments, order cancellation, stock return/quarantine/write-offs and controlled financial corrections are implemented; Oracle execution is still blocked.

## Architecture and contracts

- Browser → same-origin `/api/...` → parameterized Oracle SQL. Successful writes commit; failures roll back.
- **v6 base + additive007/008:** the existing14-table model is reused, not replaced.007 adds16 staff/identity/clinical/operational tables and links existing Prescription/Bill. 008 adds seven corrective-event/cutover tables. Planned source inventory:37 tables,31 identity columns,66 FKs,92 triggers; **not live Oracle metadata evidence**. Original migrations001–005 and the prior repair campaign are preserved. See [extension relationships](docs/MULTIUSER_MODEL.mmd).
- **Admission is authoritative:** room occupancy and retained assignment observations are projections. Direct projection edits are rejected. Former rooms remain discoverable after transfer. A legacy observation is not an invented transfer or known effective interval.
- **Scheduling:** 1–1440-minute visits ending by midnight; half-open doctor **and patient** overlap checks across active states, with adjacent visits permitted. Scheduled → Checked In → Waiting → In Consultation → Completed; cancellation/no-show rules are enforced in API and SQL. Change booking and status separately. Terminal history is read-only.
- **Finance:** `V_Invoice_Balances` computes net billed from base + items + debits − credits/refund-price-credits/write-offs/voids, and net paid from original receipts − cash refunds; outstanding is net billed − net paid. Historical Paid/Pending labels never create receipts. Zero-value invoices are Paid with zero receipts. Dashboard, registers, histories, reports, CSV and print use ledger values. Monthly collections use **receipt recording month**, while outstanding amounts are grouped by invoice month, not accounting revenue recognition.
- **Exact money:** JSON money fields are decimal strings; Oracle driver fetches Decimal; JS formats/sums BigInt cents. Each price/charge/payment ≤99,999,999.99; item quantity ≤100,000; line total ≤99,999,999.99; invoice total ≤999,999,999.99.
- Payment POSTs require a UUID key. Same normalized bill/amount/method/reference returns the original ID (HTTP 200 replay); changed payload with that key returns 409. The browser stores unresolved requests in localStorage **before sending**, retaining key/payload across close/reload, including a lost response after full settlement. Retry original details; do not submit a second payment elsewhere. Storage failure prevents submission. This records an administrative receipt, not a gateway transaction.
- Invoice date, patient and legacy label are immutable on edit. Base/items lock after any payment; notes remain editable. 008 retains originals and records manager-authorized credits/debits/refunds/write-offs; voiding is limited to unpaid administrative invoices. Cashier refunds require a recorded billed medicine return and its uncredited original-price value.
- Clinical dates are hospital-local **day-only** values, default `Asia/Kolkata`; Python, JS and Oracle use that policy. `/api/health` checks database timezone/version against API configuration; `/api/config` exposes UI policy. New payment timestamps are UTC; upgraded timestamps remain explicitly `LEGACY_UNKNOWN`. Room-history timestamps retain server-local observational semantics, **not** recovered effective clinical times.
- A bounded singleton write mutex is taken before entity locks, including BEFORE STATEMENT SQL triggers. This intentionally serializes writes for an academic workload; not a high-throughput hospital design. Lock timeout/deadlock responses are retryable 409. Supported direct writers must acquire this mutex before any explicit entity `SELECT FOR UPDATE`; privileged/manual locks can still cause conflicts.
- Legacy prescriptions remain **single-medicine instructions**, not evidence of dispensing. New quantity/context orders use explicit batch dispensing with a durable UUID, stock decrement and source-linked invoice charge in one transaction. No historical stock is assigned invented batches. Generic unjournaled stock changes are blocked for personal accounts. 008 records batch receipts/returns/quarantine/write-offs/count corrections; historical stock is an observed cutover snapshot, not invented receipts.

## Oracle setup and migration

**Read [the migration/recovery runbook](docs/MIGRATION_RUNBOOK.md) first.** Use only disposable/demo schemas; stop every writer and back up before DDL. Oracle DDL commits implicitly; a script's ROLLBACK cannot undo completed DDL.

Fresh owner schema (CREATE TABLE/VIEW/TRIGGER/PROCEDURE privileges and tablespace quota):

```sql
@sql/01_create_schema.sql
@sql/02_sample_data.sql
@sql/migrations/007_multiuser.sql
@sql/migrations/008_corrections.sql
@sql/03_useful_queries.sql
@sql/04_verification.sql
@sql/09_multiuser_verification.sql
@sql/11_corrections_verification.sql
```

01 includes `05_integrity_objects.sql` and executable invariants. Do not run001–006 on a fresh v6 installation; **do apply007 and008 once each** for the personal-account app. Seed is same-day repeat-safe, not a concurrent seed service or a reset; it never deletes records or fabricates receipts for legacy Paid labels.

Existing supported baseline: apply **only missing** migrations in order 001 → 002 → 003 → 004 → 005 → **006_integrity_repair.sql** → **007_multiuser.sql** → **008_corrections.sql**, then03,04,09 and11. 006 runs preflight data/metadata checks **before** DDL and refuses an already/partly installed v6. Existing contradictory data is a blocker for operator review, not silently repaired or deleted. Fresh/upgrade corrective object definitions are shared; their live metadata equivalence has **not** been executed here.

Use a separate restricted runtime account: owner runs `sql/07_runtime_grants.sql` plus `sql/08_multiuser_grants.sql` and `sql/10_corrections_grants.sql` for an already provisioned login. Set `ORACLE_SCHEMA` to owner when connecting as runtime. **Never grant `HMS_Internal`, DDL or broad ANY/owner privileges** to runtime. An owner/DBA can disable guards; this is not an owner-proof security boundary.

## Configure and run

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env locally: ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN; optional ORACLE_SCHEMA.
# Install/verify the schema as owner first. Then, once, at the local console:
flask --app app init-manager
# Prompts for your chosen username and password; refuses when accounts exist.
python app.py
```

Default: <http://127.0.0.1:5000>, loopback only, debug off. No DB produces structured 503 errors, not fabricated data. `HOSPITAL_TIMEZONE` must match `HMS_Settings.hospital_timezone`; change both during a stopped-writer maintenance window. Supported initial migration policy is Asia/Kolkata.

Non-loopback `HMS_HOST` requires **`HMS_COOKIE_SECURE=true`**, personal authentication and an HTTPS reverse proxy; debug is refused. Apply the same secure-cookie requirement when deploying through a separate WSGI server. Optional `DEMO_USERNAME`/`DEMO_PASSWORD` protect pages/assets/API as an additional shared Basic-auth boundary, **not** as a replacement for personal roles. Do not expose the development server publicly. This is not encryption-at-rest, privacy compliance, production identity or payment-gateway security. Never put credentials in chat or Git.

## Workflow matrix

| Area | Implemented controls and retained facts |
|---|---|
| Department / doctor / patient | Create/edit, relationships, search/filter/sort/page, details; FK-restricted master deletion. Department register previews first five names; details shows full list. Patient chart/print combines visits, admissions, observations, prescriptions and ledger invoices. Identity matching/automatic deduplication is not provided. |
| Appointments | Book/reschedule, duration, table/agenda/dated queue, doctor/patient filters, lifecycle actions, terminal retention and released time slots. |
| Rooms / admissions | Available-room admission, transfer, discharge, projection guards, former occupants and observation history; no invented pre-migration transfers. |
| Clinical / pharmacy / lab | Scoped consultation diagnoses/notes, explicit quantity orders, batch receipt/expiry/low stock, idempotent dispensing, ordered tests and retained results. Legacy instructions never prove dispensing. New clinical facts are retained, not overwritten. |
| Billing | Create base charges, notes, item add/edit/remove while unpaid, partial/full receipts, durable retry, ledger totals, complete printable invoice/receipt history. Reasoned corrective events and linked refunds retain receipts; original receipt mutation remains forbidden. |
| Reports | **14** allowlisted queries, filtering/date ranges/pagination; CSV exports all matching rows independently of visible page and neutralizes formula-prefixed strings. |
| Personal roles | Manager, doctor, patient, reception, nurse, pharmacist, cashier, lab and maintenance workspaces; server-enforced scopes, CSRF, revocable sessions, persisted counts/queues/alerts, search/page and permitted actions. See full matrix; not all advanced hospital features are supplied. |
| Shared UI | Same-origin calls; escaped text; inline errors; refresh; modal keyboard controls; narrow-screen tables; print styling. Not a completed accessibility/device certification. |

## Verification

```sh
python -B -m unittest discover -s tests -v
node --check static/app.js
node --check static/workspace.js
npm ci --ignore-scripts
npm test
npm run test:browser
npm run test:roles
```

Node 22+ is needed for the pinned browser verification packages. The Chromium helper extracts its own Linux runtime libraries outside Git. `test:browser` uses real Chromium with intercepted synthetic APIs for legacy registers. `test:roles` uses the **actual Playwright CLI and real Flask HTTP server**, with a persisted test-only SQLite compatibility fixture (workflow API payloads are not mocked; the logout-race test delays a real response), covering all roles, registration through outpatient payment/PDF, inpatient transfer/discharge/payment, maintenance and logout races. Neither is live-Oracle E2E; no SQLite production fallback exists. See the canonical campaign report for exact counts, RED→GREEN observations and final command results. For an explicitly labelled disposable SQLite rehearsal (never an Oracle fallback), see guide §10.

Opt-in Oracle tests require an account named **exactly `HMS_ORACLE_TEST`**, matching session/current schema, initialized at v6 (or v6+007+008), and:

```sh
export HMS_ORACLE_INTEGRATION=1
export HMS_ORACLE_TEST_ACK=I_CONFIRM_HMS_ORACLE_TEST_IS_DISPOSABLE
python -B -m unittest tests.test_oracle_integration -v
```

For personal-role/corrective/race tests, install007+008 and verify09+11 and also run:

```sh
export HMS_MULTIUSER_ORACLE_INTEGRATION=1
python -B -m unittest tests.test_multiuser_oracle -v
```

Both switches and the exact acknowledgement are required. These additional live tests are supplied but **not executed here**. Set credentials locally; no important schema. Tests retain synthetic clinical/financial history, finalize only their own active stays, and never disable guards/drop objects. Recreate the dedicated disposable schema outside the test harness between campaigns if a clean database is needed. Skips are not passes. Oracle concurrency, fresh/upgrade execution and restricted-runtime grants still need lab evidence. Chromium PDF receipt rendering is tested; physical printing is not.

## Files and historical evidence

SQL01–12 and migrations contain schema, samples, reports, assertions and runtime grants. `hms/` is Flask/Oracle; `static/` is UI; `tests/` contains fake/unit, DOM, real-browser-fixture and opt-in Oracle checks. [Project report](docs/PROJECT_REPORT.md), [ER model](docs/ER_DIAGRAM.mmd), [defect register](docs/DEFECT_REGISTER.md) and runbook describe v6. Older audit/design records are explicitly historical; they do not override current code or certify Oracle.
