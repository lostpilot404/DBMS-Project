# Personal accounts and role workflows

This guide describes the academic **v6 +007 +008 extensions**, not a production clinical deployment. No real patient data. Oracle installation, PL/SQL compilation, grants and races have not been executed in this environment. See [current verification/status](REPAIR_CAMPAIGN.md) and the [retained v6 runbook](MIGRATION_RUNBOOK.md).

## 1. Install and verify, with every writer stopped

Use an owner in a disposable, backed-up Oracle12c+ schema. Fresh:01 → optional synthetic02 →007 →008 →03 →04 →09 →11. An existing baseline applies only its missing001–006 first, then007/008. An existing v6 starts at007; a verified007 starts at008. **Never run001–006 on fresh01 or blindly rerun007/008.**

```sql
@sql/migrations/007_multiuser.sql
@sql/migrations/008_corrections.sql
@sql/03_useful_queries.sql
@sql/04_verification.sql
@sql/09_multiuser_verification.sql
@sql/11_corrections_verification.sql
```

007 reuses Patient/Doctor/Appointment/Admission/Room/Medicine/Bill/ledger identities; adds16 tables; extends Prescription with encounter/quantity and Bill with care context. It never infers old diagnoses, dispensing, batch allocations or receipts. 008 adds seven corrective/cutover tables and five new support views, replacing the authoritative invoice view without rewriting originals. Readiness requires `schema_version=6, multiuser_version=1, correction_version=1`. Default consultation fee0 is an explicit initial configuration, not a recovered tariff.

Provision a separate service login using the DBA's normal secret workflow. As owner run07_runtime_grants,08_multiuser_grants and10_corrections_grants for that login; configure `ORACLE_SCHEMA` to owner. Inspect actual pre-existing roles/grants; scripts do not revoke broad privileges. Never give end users Oracle credentials, HMS_Internal, DDL or ANY privileges. Do not run owner installers/postflight through the restricted service login.

DDL commits implicitly. On partial failure leave the app/writers stopped, inspect USER_ERRORS/objects/constraints/indexes and restore a rehearsed backup or prepare a reviewed forward repair. A rollback or absent marker does not undo DDL. No automated production recovery is claimed.

## 2. Bootstrap exactly one initial manager, locally

Install Python requirements, copy `.env.example` to local ignored `.env`, set Oracle service credentials/DSN/schema and hospital timezone. The API and HMS_Settings timezone must match (initial policy Asia/Kolkata).

```sh
flask --app app init-manager
python app.py
```

The CLI prompts for your username and a12–128-character password with confirmation; scrypt hashing occurs before storage. Bootstrap takes the shared write mutex and refuses if **any accounts already exist**. No production username/password is hardcoded. After account loss, ask another active manager; if none remains, use a separately reviewed local DBA recovery—not a public reset endpoint or repeated bootstrap.

For a **disposable synthetic** demonstration only:

```sh
flask --app app create-demo-accounts --ack SYNTHETIC_ONLY
```

This requires an existing active manager and creates a distinct doctor/patient, staff and one personal account per role. Random usernames/passwords are printed to the local console **only after commit**. Save them privately; no committed credentials file is created. It does not seed diagnoses, test results, dispensing or payments. Manager configures consultation fee, medicine catalogue/batches, laboratory catalogue, rooms and assignments before exercising care.

## 3. Create and manage personal accounts

Manager workspace → **Create staff record**, or register the patient/create the legacy Doctor master first → **Create personal account**.

- `patient`: exactly one existing Patient link; no staff/doctor link.
- `doctor`: exactly one existing Doctor link; no patient/staff link. Doctor remains the original master; it is not duplicated in HMS_Staff.
- Other seven roles: exactly one HMS_Staff link. Staff kind is descriptive; account role is the authorization authority.
- One account per linked patient, doctor or staff identity. Username is immutable. One role/account; multi-role users use distinct authorized identities, not a self-selected role at login.
- Manager can change role with complete matching links, reset password, activate/deactivate accounts, update/activate staff, assign doctors and ward nurses, update fees and lab catalogue activation. Staff deactivation invalidates its linked account's access. For doctors/patients deactivate the personal account.
- Account/role/password/staff updates revoke linked sessions. The last **capable active manager** cannot be removed, deactivated or relinked to inactive staff. Accounts and care/audit facts are retained, not deleted.

Sessions use opaque random HttpOnly SameSite=Lax cookies; only token hashes are stored in Oracle. Absolute lifetime8h, no sliding idle timeout. Every private request re-reads active identity; writes require CSRF and revalidate under the same database mutex. Login rotates its previous cookie/session. Logout and password change invalidate server sessions; changing your password logs out every session. Per-process bounded throttling is not a multi-worker/shared abuse-prevention service.

Remote/HTTPS deployments must set `HMS_COOKIE_SECURE=true`, use HTTPS and a properly operated reverse proxy/WSGI deployment. `python app.py` refuses non-loopback without secure personal cookies or with debug. Optional shared Basic auth is additional only. Auth bypass is accepted only by explicit TESTING harnesses. Do not treat browser hiding or client role values as authorization.

## 4. Permission boundary

| Role | Permitted work | Deliberately not permitted |
|---|---|---|
| Manager | Masters/registers/reports; account/staff/role/activation; doctor/nurse assignments; fee/test configuration; administrative corrections allowed by retained-history rules | Deleting retained clinical/financial history; rewriting receipts; changing retained original facts |
| Doctor | Own appointments; charts for previously treated or actively assigned patients; own consultations/diagnoses/notes and retained amendments; explicit Rx/test orders/cancellation; follow-up requests | Other doctor encounters; new inpatient treatment without active manager assignment; financial endpoints; completing visits via the generic status API |
| Patient | Own contact profile updates, requests, future scheduled same-doctor rescheduling/cancellation and visits, released notes/results, Rx/dispensing, admissions/room history, invoices and receipts | Other patient IDs; self-granting roles; billing mutations; unreleased clinical drafts |
| Receptionist | Registration; booking/rescheduling; request approval/rejection; queue/check-in/waiting/cancel/no-show; admission intake; maintenance request | Clinical charts/notes/results/Rx, clinical visit completion, staff roles or payments |
| Nurse | Patients with an active assigned admission; ward observations, transfer/discharge and maintenance requests | Unassigned patients; clinical prescribing/results, finance, continuing patient access after discharge |
| Pharmacist | Minimal order-linked identity, prescription quantity/instructions; medicine catalogue; batch receipt, stock/expiry/low-stock queues; explicit dispensing, medicine return/quarantine and stock write-off | General patient charts, diagnoses/notes, results, payments or direct generic inventory adjustment |
| Cashier | Minimal billing identity/context; bill/items, outstanding balances, receipts/payment recording, original-price recorded medicine-return refunds and invoice printing | General demographics/clinical chart, diagnosis/notes, prescribing or results |
| Lab | Minimal order-linked identity; tests/order/result queue, result recording and retained result amendments | General patient chart, unrelated clinical notes or billing |
| Maintenance | Rooms and nonclinical tasks, reserve/complete available-room maintenance | Patient names/IDs, clinical and financial records |

Unclassified legacy APIs are manager-only. Detail/catalogue shortcuts, summary endpoints and ID access are guarded separately. Scope is enforced on the server; forbidden methods return403 and private/unowned records normally404. A prior outpatient visit permits chart continuity, **not** a new inpatient treatment assignment. Scoped clinical charts omit finance for doctors/nurses.

## 5. Outpatient flow

1. Reception registers a Patient once. Manager links a personal patient account to that same ID.
2. Patient requests doctor/date/time, optionally linked to an owned prior consultation for follow-up. Reception accepts into the existing Appointment table (or books directly), reschedules while Scheduled, then checks in and places the patient Waiting.
3. The appointed doctor begins consultation: appointment → In Consultation; encounter + diagnosis/notes + configured consultation charge are saved together. New clinical work needs exactly one appointment or active-admission context.
4. Doctor issues quantity-bearing Rx and laboratory orders. Creating instructions **does not decrement stock**. Lab records one retained result. Pharmacy receives identified, dated batches and explicitly dispenses permitted units from a matching, nonexpired batch.
5. Dispensing uses a UUID; exact replay returns the original event, changed payload conflicts. Batch and aggregate stock, event and source charge commit or roll back together. Legacy quantity-less orders require a new clinician order; they cannot be silently treated as dispensed.
6. Doctor completes the encounter with final diagnosis/notes; appointment → Completed; patient can now read released consultation notes and result/amendment text. Patient chart also includes explicit results, observations and dispensing, not inferred events.
7. Cashier prepares a single itemized invoice for the completed encounter. Only uncancelled pending tests/unfulfilled quantities block final billing; cancelled tests never become performed services. Unbilled dispensing charges are reduced by actual returns, with original source quantities retained. Consultation/test/dispense charges are imported into existing Bill_Item once, with source links. Existing invoice ledger, exact-money limits and partial/full administrative receipts are reused.
8. Cashier records payment with its durable UUID. Patient sees only their own invoice/receipt. Print the invoice including actual receipt history; follow-up requests retain their original encounter link.

Payment entry records an administrative receipt; no card processing or gateway transaction is performed. A legacy Paid label is never a receipt. Unpaid invoice items/notes retain the v6 correction rules; payments lock charges and receipts are immutable. Original receipt mutation is forbidden;008 corrections/refunds are separate retained events (below).

## 6. Inpatient flow

Reception/manager admits an existing patient to an available Room. Manager assigns nurse account(s) to that **admission**, plus active doctor care assignment(s). Nurse sees assigned active patients and records observations. Doctor begins admission-context care, orders Rx/tests and completes ward consultation(s). Nurse transfers through the existing Admission update: former/current room observations remain separate. Open consultations block discharge. Discharge releases the room and ends nurse access.

Cashier prepares final admission invoice only after discharge and resolved orders. It gathers unbilled charges across its encounters and requires an **explicit agreed room charge**, including0 if waived. No historical tariff, room-night count or clinical effective transfer time is invented. Cashier payment and patient receipt use the same existing ledger. Duplicate final invoice context is rejected.

## 7. UI, searching and durable retries

Role navigation exposes only permitted forms and queues. Counts/notifications are SQL-derived, not sample KPIs. Alerts distinguish pending requests/tests/quantities, outstanding bills, low stock/expiry and open maintenance; they are not clinical triage or push notifications. Refresh/search/page use persisted data,40 rows per queue, stable newest-ID ordering. Source-ID inputs offer suggestions from the current page and accept another permitted ID from the queues; server ownership still applies. Advanced date/column filters remain primarily in manager registers, not every role panel.

Payment drafts are stored **before sending**, namespaced by actor and bill. Dispensing drafts are actor-namespaced, retain original UUID/payload across reload, and lock fields while uncertain. Retry original details; do not re-enter an uncertain operation elsewhere. A definitive expired/insufficient/quantity-missing/cancelled-order dispensing rejection permits correcting the draft; uncertain responses retain the key. Unavailable browser storage prevents new durable mutations, not other clinical forms.

A pre-personal-login unowned payment draft blocks new payment entry. Manager must reconcile its original key and material request against the persisted ledger before a reviewed migration/retry or disposal; **never discard an uncertain key just to unblock the screen**. Logging out clears rendered personal data, not uncertain durable financial requests. Shared-terminal/local-storage handling needs a production security design; this is a synthetic demo.

## 8. Corrective-event policy (008)

| Action | Authorization and legal transition | Persisted/stock/financial effect |
|---|---|---|
| Consultation amendment | Treating doctor or manager; original encounter Completed | Append HMS_Amendment with reason/actor/UTC; original notes/diagnosis unchanged. Both appear in released chart/timeline. Never “reopen” completed care. |
| Result amendment | Lab or manager; original result exists | Append to original result ID; original result text and order remain retained. Patient result/amendment text is released together with completed consultation; care-team access is immediate. |
| Cancel remaining Rx | Treating doctor/manager; linked quantity-bearing order with units remaining | One HMS_Order_Cancel; future dispensing blocked. Partial dispensing and charges remain facts. Returns do not silently authorize re-dispensing; obtain a new clinical order. |
| Cancel unperformed test | Treating doctor/manager; Ordered, no billed service | One cancellation event; result entry forbidden; omitted from finalization blockers/charge import. A performed result requires amendment, not cancellation. |
| Receive stock | Pharmacist/manager; matching identity/expiry, nonexpired; **UUID mandatory** | Receipt event plus batch/aggregate increment. A genuinely distinct consignment can reuse the same medicine/batch number only with identical recorded expiry and a new request key. Never re-enter an uncertain receipt under a new key. |
| Return medicine | Pharmacist/manager; original dispense, positive quantity ≤ unreturned units | Restock only verified, in-date stock; Quarantine records the return without increasing usable inventory. Neither rewrites the original dispense nor automatically transfers money. |
| Stock write-off / count correction | Pharmacist/manager write-off; manager-only positive/negative physical count correction | Signed available-stock movement with reason; cannot underflow a batch or aggregate; expired additions/restocks rejected. Both reconciliation views must remain zero-difference. Quarantine is a retained unavailable-return record, not a usable-stock bin. |
| Financial credit / debit / debt write-off | Manager; exact positive money and reason | Append HMS_Fin_Event. Credit/write-off cannot exceed outstanding balance; debit creates an explicit new receivable. Original bill/items/receipts are not overwritten. |
| Cash refund + price credit | Manager; linked original receipt and unrefunded amount. Cashier permitted **only** against a recorded billed medicine return at its uncredited original price | Atomic REFUND plus matching REFUND_CREDIT, linked by related_event_id. Optional/required stock_event_id links the approved goods return; original-price budget prevents double credit. No gateway/card transfer occurs—this records an administrative refund. |
| Void invoice | Manager; positive unpaid balance, no receipt history, administrative invoice only | Retained VOID credit and derived Voided status. Further debit/payment/item/base edits blocked. Clinical final invoices are never voided/recreated to bypass one-final-invoice rules; use credits/write-offs. |

For a **billed** return, pharmacy records goods first; cashier/manager sees **return review** with original price, credited value and remaining eligible credit. Unpaid returns use manager credit/write-off; paid returns use linked refund. Recording a return does not promise that money was transferred. General manager corrections remain possible without a goods-return link but require explicit reason and invoice bounds.

Canonical arithmetic, shared by invoices/dashboard/reports/CSV/print:
`billed = original base + items + debits − credits − refund-price credits − voids − debt write-offs`;
`paid = gross receipts − cash refunds`; `balance = billed − paid`. Gross receipt history is never silently netted or deleted. Monthly net cash uses each original receipt/refund recording month, not invoice month; outstanding uses invoice month. SQL03 intentionally retains a **gross receipt** query for v6-only compatibility; postflight12/application monthly report provide explicitly **net** collection.

All corrections require actor-bound UUID plus identical original payload. Journal receipt, event, stock/price effects and audit commit or roll back together. Uncertain journal drafts persist before send and across reload; another form/action cannot steal their key. Retry original details. Confirmed validation rejection allows editing; idempotency mismatch remains locked for review. Do not clear storage for an uncertain operation. Draft reasons/clinical text may remain in actor-namespaced browser storage: synthetic-only shared-terminal warning still applies.

008 snapshots **observed available** batch quantities and the aggregate’s unallocated legacy difference, plus a dispense-ID cutover. It does not fabricate historical receipt/dispense dates, expiry or batch allocations. Legacy unallocated stock is not dispensable through an invented batch; new verified receipts create actual identified inventory. Reconciliation reports show the legacy quantity separately.

## 9. Known incomplete/blocked scope

No automated tariffs/room-night billing, online payment/card refund execution, insurance settlement, return-to-supplier disposal logistics, patient self-registration, MFA/SSO, email reset, shared rate limiter, delivered notifications, full ward/shift staffing, regulatory signing/effective-time clinical amendment, full accessibility/device or real-PHI certification is claimed. Amendments append explanatory text; they do not replace structured prescribing or infer a corrected effective clinical time. Appointment requests are reviewed by reception; patients self-change only future Scheduled bookings with the same doctor, not checked-in or terminal visits.

The singleton mutex intentionally serializes writes. Test-only SQLite adapters cannot prove Oracle isolation, PL/SQL compilation, NUMBER semantics, rollback/races, grants or fresh/upgrade equivalence. Physical printing and human-operated clinical acceptance remain unverified. See the canonical campaign report for exact evidence, individually blocked Oracle gates and the teacher demonstration.

## 10. Teacher rehearsal without Oracle — explicit test fixture only

**Database truth:** `python app.py` uses Oracle through python-oracledb. A missing/failed Oracle connection returns503; it never loads SQLite. The separate command below deliberately runs the **test-only SQLite compatibility fixture**, not an Oracle installation. The persistent visible notice says **SQLite test fixture · Not Oracle**. Do not cite this rehearsal as evidence for Oracle migrations, triggers, grants, locks, rollback, concurrency or restart durability.

Prerequisites: Python3.10+ with `requirements.txt` installed. For pinned browser verification, Node22+ and `npm ci --ignore-scripts` are also needed. No npm frontend server/build is required; Flask serves the same-origin HTML/CSS/JS. The fixture starts with two synthetic patients/doctors, two available rooms, medicine at5, consultation20, and lab test30. Production manager/bootstrap commands above are unchanged and require Oracle6/1/1; do not use them to initialize this already-seeded fixture.

From the repository root in your activated Python environment:

```sh
HMS_TEST_PORT=5037 python -B tests/role_http_fixture.py
```

Open `http://127.0.0.1:5037`. Test-only usernames are `manager`, `doctor`, `patient`, `receptionist`, `nurse`, `pharmacist`, `cashier`, `lab`, `maintenance`; password for these **public synthetic fixtures only** is `fixture-password-only`. `patient2` and `doctor2` support isolation demonstrations. These deliberately known test credentials are not production accounts; do not expose this test server to an untrusted network or enter real data. It binds0.0.0.0 for browser-test/preview compatibility, so use a firewall/local isolated environment.

Use separate browser profiles/private contexts per actor, or sign out between roles; changing a single tab’s actor does not create a second session. Replay the outpatient/inpatient/corrective sequence in the canonical report. Initial admission assignments are empty: manager must explicitly assign the ward nurse and treating doctor. Patient contact fields prefill saved values. Choose actual IDs from the displayed queues; the fixture’s patient/medicine/test initial IDs are1/2,1,1 only for this test dataset, not an Oracle assumption. Follow-up is the doctor’s `request_appointment` action (labelled Request appointment / follow-up) with the completed encounter; reception then reviews that request.

**Safe reset:** stop this test process (Ctrl+C). Its `TemporaryDirectory` is discarded on normal shutdown; starting the same command creates a new synthetic dataset. State persists across browser reload and sign-in **during that process**, not across its restart. Abnormal termination can leave an unreferenced OS temporary directory; no automatic cleanup targets an Oracle schema or other local databases. For Oracle, retain clinical/financial events; use a separately confirmed disposable schema/DBA backup-restore procedure, not DELETEs, disabled guards or the sample-data seed as a reset command.

Verification commands are in README. `python -B -m unittest tests.test_multiuser tests.test_corrections -v` separately exercises the persisted SQLite compatibility API/domain and SQL-source contracts. `npm run test:roles` automatically starts its own fresh fixture on an allocated port. It does not attach to or clear a teacher’s running demo. `npm run test:browser` is an intercepted-API legacy smoke, not this persisted workflow rehearsal. No standalone type checker or project-wide lint configuration is supplied; scoped Ruff checks are additional static verification, not a claimed type-check pass.
