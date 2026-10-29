> **Historical phase report.** The master continuation and current completion/evidence are in [REPAIR_CAMPAIGN.md](REPAIR_CAMPAIGN.md). Its008 corrections supersede the unsupported-feature statements below; prior test counts remain historical.

> Current source-inventory correction:007 creates35 distinct triggers (one name is replaced), not36; v6+007 is70 distinct, not71. Current verifier09 now matches distinct object names; cumulative008 total92. These are source counts, not executed Oracle metadata.
# Multi-user phase — discovery and execution ledger

## Inspected starting state (2026-10-29)
Branch arena/92301fba-dbms-project, HEAD 2f8b2bb1a6ea2d21a3149a1234a8b866ea3e7cb1. Prior repair:27 modified tracked paths and13 untracked paths, no staged changes; preserved. Read REPAIR_CAMPAIGN.md and actual API/factory/DB/UI/schema. No account/session/role tables or personal login exist. Optional shared Basic auth is not personal identity. Existing14-table v6 has working source for masters, scheduling, room histories, prescriptions, ledger billing/payments/report/print. Prior19 Oracle tests were skipped; no live certification to inherit.

## Discovery matrix (before implementation)
| Role/feature | Existing state | Missing | Verification boundary |
|---|---|---|---|
| Manager | Partial: generic administrative CRUD/reports | personal account, user/staff/role control, assignments/config | prior fake/fixture tests, Oracle unverified |
| Doctor | Partial: appointments/prescription tables | own-row scope, consultation/diagnosis/notes/tests/follow-up | no role tests |
| Patient | Partial: patient chart/invoices | own login/profile isolation, appointment requests | no role tests |
| Reception | Partial: patient registration, appointments/queue/check-in | role authorization, request approval | no role tests |
| Nurse | Partial: admission/transfer/discharge | ward assignments, observations, scoped access | no role tests |
| Pharmacy | Partial: catalogue/stock only | dispensing, quantity orders, batches/expiry, care charges | explicitly not dispensing previously |
| Cashier | Partial: complete invoice ledger/items/payments/print | personal role and limited patient fields, care-charge import | reused, not replaced |
| Lab | Missing | catalogue, orders, results, authorization | no DB evidence |
| Maintenance | Partial: room Maintenance status | task queue, nonclinical access | no role tests |
| Auth/session | Missing | hash/session revocation/CSRF/rate limiting/manager bootstrap | shared Basic auth only |

## Execution plan
- [x] Baseline and failing auth/role/isolation regressions, preserve original repair.
- [x] Additive007 schema, accounts/sessions/staff, fail-closed authorization, bootstrap/demo CLI.
- [x] Scoped clinical/ward/lab/pharmacy/appointment-request/care-charge workflows, reuse existing ledgers.
- [x] Personal login, role dashboards/queues/forms, permitted navigation and print/reload.
- [x] Cross-role persisted test-double and real-browser checks; opt-in Oracle expansions.
- [x] Final verification/status matrix, setup/migration/limitations; separate self-review.

Decisions: one role/account with validated doctor/patient/staff link; explicit manager assignments. Server-side session tokens stored hashed, CSRF on writes, re-read active account per request. Default authentication ON; prior test harnesses explicitly opt out solely to preserve legacy subsystem tests. Existing generic endpoints remain guarded centrally and scoped; roles gain dedicated workflow endpoints rather than an unrestricted generic SQL interface. New clinical/prescribing/dispensing facts are not retroactively invented. Oracle absence blocks certification, not implementation. No commit/push/reset/clean/stash/branch switch.


## Delivery status —2026-10-29

**Core academic role workflows implemented and tested locally. Oracle certification BLOCKED; advanced clinical/stock correction scope remains PARTIAL.** Not a production-ready hospital/EHR claim.

Working branch remains `arena/92301fba-dbms-project`, HEAD `2f8b2bb1a6ea2d21a3149a1234a8b866ea3e7cb1`. Starting dirty work was preserved; no reset/clean/stash/branch switch/commit/push/merge was performed. Historical001–005 and REPAIR_CAMPAIGN were not replaced. Prior campaign evidence is historical, not new Oracle evidence.

### Current feature matrix

| Feature / role | Implementation | Tested here | Partial / blocked boundary |
|---|---|---|---|
| Personal identities/sessions | Database-backed scrypt accounts, opaque hashed session tokens, HttpOnly/SameSite,8h expiry, CSRF, rotation/logout/revocation, bounded throttle; default auth ON | Persisted SQLite role/session/expiry/password/staff tests; real HTTP/Chromium all9 logins/reload/logout | Oracle persistence/locking BLOCKED; shared multiworker limiter/MFA/SSO/recovery PARTIAL |
| Manager | Staff/accounts/roles/activation/reset, last capable-manager protection including inactive relinks; doctor/nurse assignment, consultation/lab fee/config, lab activation; reused masters/reports | API permission/activation/uniqueness/bootstrap/demo tests; real forms create staff/account; original register browser suite | Not an unrestricted history editor; clinical amendments and financial reversals absent |
| Doctor | Own schedule, assigned/previously treated charts, own encounters/diagnoses/notes, quantity Rx/tests, follow-up | Persisted outpatient/inpatient/isolation tests; real browser both flows | New inpatient work requires active doctor assignment, not historical visit alone; note/order amendment/cancellation PARTIAL |
| Patient | Own demographics/visits/admissions, released notes/results, Rx/explicit dispensing, requests/followup, invoices/receipts/history | IDOR/direct API tests; real browser newly registered/link-created patient through paid invoice/PDF; inpatient chart | View-only profile; no public self-registration or gateway payments; drafts not released |
| Reception | Registration, booking/reschedule, request decisions, check-in/waiting/cancel/no-show, admission intake, maintenance request | Actual registration → linked account → request → accepted/rescheduled booking → queue browser flow | Clinical/financial shortcuts forbidden; advanced role-panel filters limited |
| Nursing | Active admission-level assignment, observations, transfer/discharge; old care/history retained | Persisted role tests and real browser transfer/discharge; post-discharge scope removed | Not a ward/shift staffing product; Oracle projection/rollback/races BLOCKED |
| Pharmacy | Catalogue, explicit batch receipt, actual low-stock/expiry alerts, quantity/expiry/medicine checks, UUID replay, atomic event/stock/charge | Persisted workflow, expired/excess rejection and injected post-stock rollback tests; real browser receipt/dispense/reload | No inferred legacy dispensing or batch allocation; returns/write-offs/stock ledger corrections PARTIAL; Oracle race unexecuted |
| Cashier | Shared item ledger, final outpatient/admission invoice, source-linked import once, outstanding/partial/full receipts, durable payment retry and print | Persisted60.00 outpatient/120.00 inpatient reconciliation; browser payment, patient receipt and PDF render | Room charge is explicitly agreed, not inferred tariff; no refunds/reversals; physical print BLOCKED |
| Lab | Compatible catalogue/order/result tables, minimal identity, retained one-time results; manager edit/activation | Persisted and real browser order → result → bill integration; forbidden manager-config test | Result amendment/cancellation not supplied; no analyzer integration |
| Maintenance | Nonclinical room/task queues, Open → InProgress → Completed; occupied-room rejection | API occupied-room regression; real browser reserve/release; no patient names in worker view | Optional small workflow, not full facilities product |
| Role dashboards | SQL counts/scoped queues/actual actionable alerts, search,40-row paging with stable ordering; source ID suggestions/manual permitted IDs | All9 workspace policies; real HTTP browser reloads and clinical queue propagation | Refresh, not push/delivery notifications; advanced date/column role filtering PARTIAL; not triage |
| Connected outpatient | Registration → account link/request → booking/reschedule/check-in → consult/Rx/tests → dispense/results → itemized bill/payment/receipt → followup | Persisted backend and real Flask/Playwright workflow; PDF receipt inspected | Oracle end-to-end BLOCKED; unavailable/cancelled care cannot be fabricated just to finish invoice |
| Connected inpatient | Admission → assignment/care → retained transfer → completed review/discharge → explicit final bill/payment/receipt | Persisted backend and real Flask/Playwright workflow; room IDs/history checked | Oracle trigger/transaction/persistence equivalence BLOCKED |
| Additive007 / grants / verification |16 extension tables; reuse all existing masters/ledger; marker on v6;08 grants and09 postflight supplied | Source inventory, FK/index/trigger/retention review; Python source compilation only | Oracle DDL/PLSQL execution, grant denial/allowance and upgrade equivalence BLOCKED |

### Final evidence, separated by level

- **Python full:**143 tests,120 passed,23 skipped (19 prior Oracle +4 new opt-in Oracle); zero failures/errors. Command: `python -B -m unittest discover -s tests -v`. New focused role/security/workflow suite:34 tests passing. Existing subsystem harnesses explicitly use test-only auth bypass; new role suite has auth enabled.
- **Mocked DOM:** `npm test`,9/9 passing. Includes durable payment reload, exact money/print and personal-cashier refresh / unowned historical-payment safeguards. Not server/Oracle evidence.
- **Historical-register real Chromium fixture:** `npm run test:browser`,9 modules/14 reports/39 synthetic API calls; payment reload retry, invoice print action,390×844 view;0 page errors. Deliberately isolates legacy admin registers from personal auth.
- **New actual Playwright CLI / real Flask HTTP:** `npm run test:roles`,6/6 passing. All9 personal logins/forbidden admin access/reload/logout/invalid login; full registration-to-outpatient payment/PDF with patient isolation; manager staff/account forms; delayed-response-after-logout protection; inpatient assignment/observation/transfer/discharge/payment/retained chart; maintenance isolation/lifecycle. Workflow responses are actual Flask/SQLite responses, not mocked API payloads. The logout-race case deliberately delays a real captured HTTP response.
- **Persistence boundary:** browser fixture uses a temporary on-disk SQLite database and the real app/auth/workflow routes. It survives browser reloads within that server. Compatibility adapters translate selected Oracle syntax and provide test projection triggers; SQLite serialization/types/locks/constraints **cannot certify Oracle**. No SQLite production fallback was added.
- **Compiler/source checks:** app/hms/tests Python `compile()`; both JavaScript syntax checks; new Python F/I import/undefined/unused checks; `git diff --check`. SQL identifiers/inventory/FK leading indexes and actor/endpoint policies self-reviewed. These are not SQL compilation.
- **PDF:** actual Chromium PDF and print-mode screenshot generated outside Git; inspected patient name, three source items20+30+10, paid60/outstanding0 and a retained UTC receipt. Physical printer output remains unverified.
- **Oracle:** no service/client/container available; all23 skips remain BLOCKED, not passes. Four new opt-in tests cover object compilation/roles/IDOR, outpatient/receipt/followup, two-client dispensing race and ward transfer/final invoice; they have never run here.

Reproduction/setup: [MULTIUSER_GUIDE](MULTIUSER_GUIDE.md), [runbook](MIGRATION_RUNBOOK.md), README commands. Temporary logs/browser outputs are not committed datasets. Tests require installed Python requirements, `npm ci --ignore-scripts` and Node22+.

### RED → GREEN and review record

Observed regressions before fixes included default API privacy/module/migration discovery; optional text input handling; unfinished consultation billing; CLI missing Flask application context; cashier payment refreshing the forbidden admin dashboard; receptionist clinical detail shortcut returning200; old doctor visit granting new inpatient treatment; clinician summary bypassing financial policy; known batch undercut and occupied-room maintenance; omitted room fee silently treated as zero; inactive/last-manager relinks; duplicate personal-master links; and remote shared Basic auth without secure personal cookies. Assertions were retained; test-fixture syntax/date/selector readiness issues were diagnosed rather than weakening expected results.

Real-browser debugging additionally found missing admission UI/room source IDs, unstable queue ordering, old legacy-fixture bootstrap incompatibility and reload-before-queue test timing. The role workflows were rerun after corrections. Final source review rechecked central endpoint defaults, direct-ID policy, same-transaction write revalidation/audit, active physician/nurse assignment, session revocation and stale response rendering, source-charge/stock rollback, historical payment keys, bootstrap safety, additive SQL, FK coverage and restricted grants.

**Review limitation:** actual Superpowers plugin/subagents/independent reviewer were unavailable. Available skill instructions were consulted and TDD/debug/verification methods adapted directly. This is disclosed **self-review**, not independent approval.

### Exact remaining release gates

1. Run fresh v6+007 and supported001–007 upgrade in separate explicitly disposable Oracle schemas; compile every PL/SQL object and inspect USER_ERRORS. Validate30 tables/27 identities/48 FKs/71 triggers from actual metadata, not source counts.
2. Exercise implicit-DDL commit/partial-failure recovery,09 postflight, FK/index coverage, NUMBER/DATE/TIMESTAMP and hospital-timezone behavior. Do not resume writers on partial markers.
3. Run07+08 as owner, then exercise each API/CLI as restricted runtime; verify intended SELECT/INSERT/UPDATE and intentional session DELETE, and deny history/audit/result/dispense mutation, DDL/ANY/HMS_Internal and broad inherited roles.
4. Run both Oracle suites and manual two-client stock/order/payment/booking/transfer races, late rejection/rollback, account revocation during writes, pool saturation/lock timeout, restart persistence and fresh-upgrade equivalence. SQLite mutex behavior is not equivalent evidence.
5. Clinical amendments/cancellation, stock returns/write-offs and full operational tariff/correction protocols remain explicitly PARTIAL; pending orders block billing rather than fabricate service completion. Financial reversals remain unsupported. Production privacy, recovery, shared throttling, accessibility/device and physical print acceptance require separate work.
