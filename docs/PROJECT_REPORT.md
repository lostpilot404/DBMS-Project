# Hospital Management System — technical report (v6, 2026-10-29)

> This is the retained v6 technical description. Current personal-role and008 corrective-event architecture,37-table source inventory, legal transitions and verification limits are documented in [REPAIR_CAMPAIGN.md](REPAIR_CAMPAIGN.md), [MULTIUSER_GUIDE.md](MULTIUSER_GUIDE.md) and [extension ER](MULTIUSER_MODEL.mmd). Statements below about absent dispensing/refunds describe v6 only.

## 1. Scope and architecture

BCSE302P academic synthetic-data application: Oracle12c+ relational database, Flask/python-oracledb, semantic HTML/CSS/plain JS. The original nine-entity assignment model is retained and extended with room observations, invoice lines/payment events and two infrastructure relations. It is not a clinical record system, dispensing service, financial settlement platform or production deployment.

Flow: browser same-origin API → allowlisted/parameterized SQL → Oracle transaction → response → explicit list/ledger refresh. Failed writes roll back. Multi-query dashboard, patient summary, record details and invoice ledger use read-only transaction snapshots. Health checks schema version and hospital-day policy. No configured Oracle yields a structured unavailable state rather than fake KPI values.

## 2. Relational model and normalization

[ER diagram](ER_DIAGRAM.mmd) matches fourteen tables: Department, Doctor, Patient, Appointment, Room, Admission, Admission_Room_Stay, Medicine, Prescription, Bill, Bill_Item, Bill_Payment, HMS_Settings and HMS_Write_Mutex. Twelve business identity keys; thirteen restrictive FKs. There are 35 intended final triggers and 64 explicitly named business constraints checked by verification, plus infrastructure PK/check constraints. Counts are source inventory, **not live metadata observations**.

| Relation | Principal facts / dependencies |
|---|---|
| Department | Identity, unique name, location; doctor association is FK-derived. Register shows a bounded first-five-name preview; details returns the complete list. |
| Doctor | Identity, name, specialty, nullable unique contacts, required department. No professional registration/roster model. |
| Patient | Identity, name, day-only DOB, constrained gender/blood group and contact/address. Unique phone is the assignment policy, not a proof of patient identity. Shared-household matching/merging is not implemented. |
| Appointment | Patient/doctor, hospital day, HH:MM, duration, lifecycle state. Virtual unique active keys plus compound interval guard cover both patient and doctor. |
| Room | Identity, number/type, derived occupied state (or unoccupied Available/Maintenance). One active occupant per room; no bed-capacity model. |
| Admission | Patient, current/last room, day-only admission/discharge. One active stay per patient/room. Clinical effective transfer times are not captured. |
| Admission_Room_Stay | Retained room observations; LIVE recording timestamps or LEGACY unknown intervals. Admission is authoritative; projections cannot be directly edited by runtime users. |
| Medicine | Catalogue, price, stock count. Atomic adjustment is not a stock-movement or dispensing ledger. |
| Prescription | Patient/doctor/medicine, instructions/duration, day. Single-medicine order; no inferred administration, quantity dispensed or inventory decrement. |
| Bill | Patient, immutable issue day/legacy label, three base charges, virtual base sum, notes. |
| Bill_Item | Bill FK, description, integer quantity, price, virtual line total. Bill ownership is immutable; no changing settled charges. |
| Bill_Payment | Bill FK, amount/method/reference, unique idempotency key, recording time/basis. Append-only administrative receipt; no gateway capture or refund model. |
| HMS_Settings / HMS_Write_Mutex | Version/hospital timezone; singleton transaction lock. Infrastructure, not new clinical entities. |

Separation of master data, association/history rows and payment events removes repeating groups and common update anomalies. Surrogate keys alone do not prove 3NF. Room status is an intentionally materialized projection guarded by Admission. Financial balances/status are a **view**, not redundant editable facts. Historic names/departments remain current-master joins; the project does not claim immutable demographic snapshots.

## 3. Integrity and transactions

- API mutex first; Oracle BEFORE STATEMENT locks cover direct ordinary DML. Global serialization is deliberate for academic throughput, with five-second waits and retryable timeout/deadlock API errors. It is not universal owner-proof deadlock prevention.
- Internal projection package uses private state with exception cleanup; runtime receives no package execution/DDL. Unified admission writer maintains Room and room observations atomically. Owners/DBAs can bypass any trigger and are outside the runtime boundary.
- Appointment intervals are half-open; adjacency allowed. Lifecycle/booking edits are separate operations; terminal history cannot be rewritten/deleted. Admission patient/day and discharged history cannot be rewritten; discharge and transfer must be separate.
- Established appointment/admission/prescription/bill/payment/room-observation history is retained. Runtime grants omit destructive history operations. Master deletion remains FK-restricted.
- `V_Invoice_Balances` is shared across register, dashboard, histories, ledger, financial reports and SQL examples. Base + lines = billed; actual payment sum = paid; billed − paid = balance. Legacy Paid labels never fabricate receipts. Zero invoice balance implies Paid even with no receipts.
- Idempotency compares normalized bill, amount, method and reference before balance checks; matching repeat returns original ID, changed reuse conflicts. Browser saves unresolved material request before sending and retries unchanged after close/reload, including full settlement. LocalStorage unavailable → no submission.
- Notes may change after payment; issue day/legacy label/ownership cannot. Charges lock after first receipt; reversals/refunds are explicitly unsupported and rejected. Invoice print includes every returned item and receipt plus balances/disclaimer.

## 4. Date, money and reporting policy

Hospital day defaults Asia/Kolkata (ZoneInfo/Intl/Oracle HMS_Today). Critical DATE values normalize to days; migration refuses non-day legacy data pending operator review. UI uses hospital-zone date rather than browser timezone. Version/timezone mismatch fails readiness. New payment recording timestamps are UTC; legacy zones remain UNKNOWN rather than fabricated. Room timestamps are server-local observations, not known clinical effective times; midnight observations stay timestamps in JSON.

Money stays Decimal from Oracle through exact JSON strings. JS uses BigInt cents for display and previews. Quantity ≤100000; each charge/unit price/payment and item line ≤99999999.99; invoice ≤999999999.99. Both SQL and Python enforce relevant bounds; no binary-float money serialization. Reports use fourteen allowlisted definitions; paginated display and full filtered CSV share query construction. CSV neutralizes spreadsheet formula prefixes. Monthly collections are actual receipt recording-month totals, while current outstanding amounts use invoice month; neither is recognized revenue accounting. Unknown old payment timezone falls back to stored calendar month, explicitly disclosed.

## 5. Installation, migration and deployment

Fresh 01 includes corrective shared 05 and invariant 06; then sample02, reports03, verification04. Upgrade: only missing preserved001–005, then new006, reports and verification. [Runbook](MIGRATION_RUNBOOK.md) specifies prerequisites, fail-fast checks, partial-DDL recovery and restricted-runtime grants. DDL is not atomic/rerunnable. Stop all writers, back up, rehearse disposable copies and verify before resuming. No schema has been migrated here.

Default app binding is loopback/debug-off; optional Basic auth is mandatory for non-loopback entrypoint binding. All pages/assets/API are protected when configured. Remote synthetic demos require a trusted HTTPS proxy. This is not enterprise authentication, roles, immutable operator audit, encryption-at-rest, clinical privacy compliance or a payment-security implementation.

## 6. Verification and limits

[Campaign evidence](REPAIR_CAMPAIGN.md) is authoritative for fresh test counts and RED→GREEN results. Python fake/unit tests, mocked DOM tests, real headless Chromium using intercepted synthetic API fixtures and opt-in live-Oracle tests are separate categories. Browser fixtures exercise all nine modules/fourteen reports, lost-response retry after reload, exact money, export and print-media layout. They do not establish persistence, Oracle locking/trigger compilation, browser-to-Flask-to-Oracle E2E, physical printing, accessibility certification or manual two-session acceptance.

Live Oracle remains unavailable; required lab work includes fresh/upgrade equivalence, rollback/multirow/mixed-lock races, runtime-user grants and actual SQL dictionary checks. Oracle absence blocks certification, not the source implementation. Generic Superpowers instructions were followed directly because actual plugin/subagent/reviewer tools were unavailable; separate self-review is disclosed, not independent review.
