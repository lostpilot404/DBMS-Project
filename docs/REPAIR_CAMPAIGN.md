# HMS full repair campaign — results, 2026-10-29


## Final release — 2026-10-29

**Readiness: Demonstration-ready with stated limitations.** The verified environment is Flask plus an explicitly labelled, disposable SQLite compatibility fixture and Chromium153—not Oracle. Normal `python app.py` still uses Oracle and fails503 when it is unavailable. All production/default credentials remain operator-chosen; fixture passwords are public synthetic test data only. Guide §10 is the reproducible no-Oracle teacher rehearsal; the Oracle path and safe migration order remain in README/runbook. No frontend build/server is required.

### Release verification

| Category / actual command | Result / database truth |
|---|---|
| `python -B -m unittest discover -s tests -v` | **172 total:146 passed,26 skipped,0 failures.** Includes3 actual HTTP checks (new explicit-fixture-label check), unit/contract and compatibility tests;19 prior Oracle +7 role/correction Oracle cases skipped. |
| `python -B -m unittest tests.test_multiuser tests.test_corrections -v` | **59 passed**,0 failures/skips;55 SQLite API/domain tests plus4 SQL-source contracts. This subset is already included in172, not59 extra tests. |
| `npm test` | **10 passed**,0 failed/skipped; mocked DOM/API. Added regression catches falsely claiming Oracle from a healthy fixture; existing9 tests retained. |
| `npm run test:roles` | **11 passed**,0 failed/skipped; actual HTTP→Flask→temporary on-disk SQLite, real Chromium. Same nine roles/OP/IP/corrections/print/retry coverage, plus visible fixture and CSP/dashboard-label assertions. |
| `npm run test:browser` | Legacy intercepted-API Chromium smoke:9 modules/14 reports/39 mocked calls,0 page errors; not persisted Oracle evidence. |
| Python/JS/static SQL/lint |17 Python files compile; all7 JS/CJS files parse; scoped `ruff check hms tests --select F,I --no-cache` clean;9 dedicated SQL-source contract tests pass; all SQL includes and key documentation paths resolve. No configured standalone type checker/project-wide lint exists; Oracle SQL compilation is **not executed**. |
| Git/security review | Full project-file manifest and tracked/untracked diffs reviewed; no unrelated source or sensitive configuration found. Secret-pattern/path checks report no candidates; `.env` absent and ignored, only safe template. Historical001–005 unchanged; valuable tests, fixtures and evidence retained. `git diff --check` passes. Self-review only; independent reviewer/plugin unavailable. |

Release checks use the installed Python dependencies (`PYTHONPATH=/tmp/hms-deps` in this sandbox); a normal activated venv uses README commands without that sandbox prefix. Logs `/tmp/hms-release-*.log` are local execution evidence, not committed runtime artifacts. Detailed earlier RED→GREEN and domain matrices below remain applicable unless explicitly superseded here.

### Directed browser and teacher acceptance

Nine role screens were visited and visually inspected at1280px; actual form journeys were repeated against a separate running synthetic fixture: OP through bill/payment/receipt, personal staff-account creation, nurse-scoped IP observation/room1→2/discharge/120 payment, maintenance lifecycle, and amendments/cancellations/return/refund/write-off. The persisted invoices reconcile60 +120 +55 =235 net billed/collected, all balances0; original30+30 receipts remain alongside5 refund/credit and reasoned2 debit/write-off. Additional requests verified legal booking201, same-doctor overlap409, encounter-linked follow-up201, private accounts403 and logout/session401. Agent visually read the retained-amendment chart, refunded invoice print, actual manager dashboard and settled390px mobile view (no overflow; closed sidebar right edge0).

The live review caught two new truth-in-demonstration issues: an inline fixture notice violated the existing CSP (fixed by reusing external `.work-alert` CSS; observed Chromium RED→GREEN without relaxing CSP), and legacy dashboard text called every healthy backend Oracle (observed DOM RED→GREEN; runtime labels now database-neutral). The fixture alone inserts the **SQLite test fixture · Not Oracle** notice; normal application HTML has no fixture banner/fallback. HTTP/body, real browser and CSP assertions protect that boundary.

Exploratory driver errors (missing relative-URL base context, wrong direct booking endpoint and a screenshot during a responsive transition) were corrected and the claimed checks rerun. Browser console output retained expected unauthenticated `/api/auth/me`401 probes, with no JS page errors or unexpected CSP/console failures in the corrected run. This is agent-directed browser automation and visual inspection, reusing tested form helpers—not a human physical-device/clinical/Oracle acceptance or an independent review. Physical printing and the precise Oracle gates below remain blocked.

### Cleanup and recoverability

Removed only19 reproducible ignored files in `.ruff_cache/`, `hms/__pycache__/` and `tests/__pycache__/`; later regenerated caches are removed again before final status. No application source, migration, regression test, seed, historical report or required screenshot was deleted. No repository logs/databases/screenshots/private configuration required removal. Ignored `node_modules` remains a local verification dependency, not part of the submission. Added ignore rules for disposable SQLite databases/sidecars, browser/test reports, coverage/type caches, browser profiles and root transient logs; required SQL/tests/docs/assets remain visible.

Verified external backup directory: `/home/user/hms-release-backups/20261029T064255Z-18ce7f`. `all-remote-refs-before-release.bundle` captures full history and both obsolete branch refs; `reviewed-and-untracked-worktree.tar.gz` +binary patches preserve the original dirty work, which Git bundles alone cannot capture. Bundles were verified by Git, tar/gzip integrity read and SHA256 checks passed. A post-release bundle is added there after publication; the directory is outside the repository and is not committed. No destructive Oracle reset is provided; test-fixture restart alone resets its own temporary synthetic database. Audit processes are stopped at completion.

### Final release provenance / branch cleanup

- Actual default/final integration branch: **`main`**, verified through GitHub metadata. Tested submission commit: **`2bb2535aec6b880fdb3291a7e7f397d006a633f0`** (`Finalize HMS workflows and submission readiness`).
- Actual GitHub merge: [PR#3](https://github.com/lostpilot404/DBMS-Project/pull/3), **MERGED** at2026-10-29T07:00:57Z; application release integration commit on main: **`208523ef7a2d837dcd7f1630f77176448de1a5d3`**. Fetch verified it remotely; local main and the required session branch were fast-forwarded to that commit without switching branches. `git diff 2bb2535aec6b880fdb3291a7e7f397d006a633f0 208523ef7a2d837dcd7f1630f77176448de1a5d3` was empty: the merge preserved the exact tested release tree. No CI checks were configured on the PR; local checks above and disclosed self-review are not represented as CI/human approval.
- Deleted obsolete **remote** branches after fresh protection/head-SHA/ancestry checks and verified external backup: `arena/fec8be83-dbms-project` at `2744af89f38c4538e8446d2647ae6347ae42697c`, and `fix/hms-final-validation-ui` at `5db998c9c2205baee51e3718bd724a7a3aba28a2`. Both were unprotected, authored by this repository owner, had **0 unique commits** versus main, and were already integrated. GitHub deletion succeeded; a fresh remote branch listing showed them absent and fetch/prune removed their tracking refs. No unique work was discarded.
- No obsolete **local** branches existed to delete. Remaining local/remote branches: `main` (the final/default branch) and `arena/92301fba-dbms-project` (mandatory active Arena session/source branch; deliberately retained). `origin/HEAD` is a symbolic alias for main, not another project branch. No protection bypass, force push, history rewrite, branch switch or schema deletion was used.
- This provenance is a subsequent **documentation-only** finalization on the same source branch, published through the same reviewed PR/merge workflow. The immutable application release hashes above do not purport to be the hash of this self-containing document. A commit cannot embed its own hash. Obtain the current full documentation-inclusive final tip with `git fetch origin` then `git rev-parse origin/main`; the final execution response also gives the actual post-finalization hash. All code/test/SQL content is unchanged by provenance finalization.
- External backups remain at the directory above: initial full-history/ref bundles, the original dirty-worktree archive/patches, `verified-submission.bundle`, `before-obsolete-branch-deletion.bundle`, copied verification logs/screenshots, and the final reference snapshot `final-release.bundle`. Git verifies the bundles and SHA256 checksums; no backup/evidence/database artifact is committed into the application repository. Initial work is preserved as committed source plus the independently readable original-worktree archive.

Final teacher instructions are README and MULTIUSER_GUIDE (especially §10 for explicit SQLite rehearsal); no undocumented DB edits are required. All audit servers/Chromium processes started by this release were closed after inspection. A clean worktree is obtained by reviewed commits, not by discarding source or tests. Historical Git/count statements below describe earlier checkpoints, not the final release.

**Outstanding certification:** no Oracle credentials/DSN/schema/acknowledgments, `.env`, client/listener/container service were available on recheck. Fresh/upgrade/metadata/PLSQL/grants/DDL recovery, Oracle rollback/locking/races/NUMBER/timezone/restart/equivalence remain individually **Blocked** as detailed below. Unsupported production features and shared-terminal draft privacy limits in the master assessment remain unchanged. Do not market this college demonstration as Oracle-certified or real-patient-ready.

---
> **Historical implementation-phase assessment (release results above supersede Git state and counts):** [Master continuation — final assessed status](#master-continuation--final-assessed-status-2026-10-29) below supersedes the historical v6 findings/counts in the first sections.171 Python tests (145 pass/26 Oracle skips),11 real role-browser cases; corrective workflows implemented. **Demonstration-ready with stated limitations; Oracle execution blocked.**

## Historical v6 campaign — retained evidence

## Overall outcome

**Repair implementation completed across SQL, Flask, frontend, histories, reports, payments, printing, migration checks and documentation. Live Oracle certification is still blocked, not passed.** H01–H03 and H05–H15 have implementation/non-Oracle evidence; H04 is the explicit remaining infrastructure/evidence blocker. No claim is made that unexecuted triggers compile or that Oracle races/rollback/migrations work merely because source/unit tests pass.

The application remains an academic **synthetic-data** demo. Refunds/reversals are explicitly unsupported; prescriptions are instructions, not dispensing. No lost room transfers, historical intervals, receipt timestamps or payments were invented.

## Actual checkout and preservation

- Root: `/home/user/DBMS-Project`.
- Active branch: `arena/92301fba-dbms-project`; no configured upstream.
- HEAD before and after: `2f8b2bb1a6ea2d21a3149a1234a8b866ea3e7cb1`.
- Campaign began with a clean tracked/staged/untracked state. Final state: modified/new files listed below, **uncommitted and unstaged**, on the same branch. No deleted tracked paths.
- Historical migration001–005 files were byte-compared with HEAD and are unchanged.
- **No commit, push, PR/merge, reset, clean, stash, checkout/branch switch, history rewrite, or removal/discard of starting work was performed.** Dependency installations, browser libraries, logs and screenshots were kept out of Git; node_modules is ignored. No persistent server is required; actual-HTTP tests shut down their own ephemeral servers.

## Method and RED → GREEN evidence

The actual Superpowers plugin, skill-invocation interface, subagents and independent reviewer were unavailable. Eight published skill instructions were fetched/read and their engineering method followed directly: inspect baseline, plan, regression before behavior changes, diagnose failures, implement, focused/full verification, separate self-review. This is **not** a claim that those unavailable tools or an independent reviewer were invoked. The durable checklist is [the execution plan](superpowers/plans/2026-10-29-hms-repair.md).

Baseline: **66 Python tests:53 passed,13 Oracle skips**. Initial repair regressions:18 tests,19 expected assertion failures including subtests, no errors (`/tmp/hms-red.log`). After implementation those regressions pass. New frontend regressions initially failed6/6, then passed; later stale-financial-label regression also failed before its fix. Additional observed RED→GREEN cases covered reversal/readiness, midnight observation precision, bounded department aggregation, remote debugger refusal, case-normalized legacy UUID lookup/uniqueness, patient-chart balance details and integer-zero money encoding.

Real Chromium screenshot/layout review found a bug that mocked DOM did not: print-media invoice began at **y=602**, leaving the first page blank. Added failing top-position assertion; CSS now removes the hidden app-shell from print layout, **y=0**, with items, receipts and balances visible. The final print screenshot was examined. No physical printer/PDF output was certified.

Compatibility adjustments in existing tests were intentional harness/contract changes, not removal of assertions: infrastructure lock/read-only SQL is separately recorded; raw first-lock regression still proves mutex order; fake handlers recognize the new view/hospital clock and nested COUNT query; money assertions now require exact strings; patient summary includes an extra history query. One regression imported a Blueprint rather than the API module and was corrected to use import_module. DOM tests corrected absent-control access via namedItem. Browser harness corrected toast selector and allowed native data/blob assets. No behavioral test was weakened/deleted solely for green.

## Findings, exact repairs and evidence

| ID | Status | Changes and tests |
|---|---|---|
| H01 | Implemented; Oracle pending | `05_integrity_objects.sql`: Room/stay write guards, private-state projection package with exception cleanup, unified Admission sync. `07_runtime_grants.sql` excludes package/DDL/history mutation privileges. SQL contracts and opt-in projection/rollback tests. |
| H02 | Implemented; Oracle pending | `V_Invoice_Balances`; API bills/dashboard/four financial reports/summary/ledger and SQL03 use actual ledger arithmetic; UI report labels/columns corrected. `SqlContractTests`, zero-value invoice, money boundaries, timeline ledger and browser print checks. |
| H03 | Implemented | `add_bill_payment`: normalized matching replay before balance check, changed/cross-bill reuse409, original ID200. Case-normalized unique index supports old uppercase UUIDs without rewriting rows. JS persists material request before send and restores locked retry across reload. Fake replay/mismatch tests; DOM; Chromium lost-response+reload+same-payload replay; opt-in concurrent-key test. |
| H04 | **BLOCKED** | No Oracle service/config/client/container. Nineteen opt-in tests skipped; no DDL applied or live metadata/race/rollback observations. |
| H05 | Implemented; Oracle pending | Immutable date/legacy label/patient, notes field editable after receipts, charge/item lock, preserved item ownership guard; editor omits immutable/settled fields. API metadata tests and DOM notes-only PUT; opt-in direct SQL guards. |
| H06 | Implemented | Details API includes complete items/payments; print table includes receipt ID/method/reference/time basis/amount and actual balance/disclaimer. CSS print layout fixed. DOM contents, real Chromium click/print-media position and examined screenshot. Physical printing pending. |
| H07 | Implemented; Oracle pending | `_patient_timeline` separates original admission from observed assignment; legacy interval explicitly unknown. Room details join immutable stays to find former occupants. Patient bill timeline includes receipts total/balance. Timeline regressions; query review; opt-in transfer rollback test. |
| H08 | Implemented; Oracle pending | SQL combined status/booking rejection; compound half-open overlap for doctor **and patient**. API patient overlap precheck. Existing lifecycle regressions plus opt-in direct SQL/patient-across-doctors cases. |
| H09 | Implemented mitigation; live races pending | `_transaction` mutex first, SQL BEFORE STATEMENT mutex on12 business tables, bounded waits on scheduling/ledger locks, ORA54/60/30006 →409. Raw-call lock-order/deadlock regression; gated races. Arbitrary privileged explicit locks still need protocol. |
| H10 | Implemented; execution pending | New006 preflight/shared installer/postflight, missing/invalid/disabled object and invariant errors; version6 published only after successful assertions. Fresh01 and upgrade006 share05. SQL source contracts/inventory; actual fresh/upgrade equivalence/recovery pending. |
| H11 | Implemented; Oracle pending | ZoneInfo/Intl/HMS_Today hospital day, day-normalizing guards/defaults, schema/timezone readiness check, exact observation timestamp encoding, new payment UTC vs legacy UNKNOWN. Midnight/config/date/timestamp regressions and label review. |
| H12 | Implemented | oracledb≥3.4 Decimal fetch, keyed exact-string money (including integer zero), numeric IDs kept integers; bounded quantity/line/invoice amounts; JS BigInt cents. Large-cent, zero/ID, limits, DOM and Chromium formatting tests. |
| H13 | Implemented; Oracle pending | Retention guards for appointments/admissions/prescriptions/bills/payments/stays; runtime grants restricted. Oracle harness no longer attempts forbidden history deletion or disables guards; finalizes own active stays and leaves synthetic history. Source tests; opt-in direct deletion checks. |
| H14 | Updated | README, technical report, ER, defect register, runbook, manual matrix/log and historical audit headers reconciled. Current source inventory14 tables/12 identities/13FK/35 triggers;14 reports. Prior45/66-test and no-browser statements labelled historical. |
| H15 | Implemented academic boundary | Loopback entrypoint default, optional configured Basic auth on all routes/assets, remote bind requires both credentials, remote debugger refused, synthetic-only UI/docs. Auth fake/actual HTTP tests and entrypoint regression. Not enterprise security/real-PHI readiness. |

Additional self-review: bounded LISTAGG preview avoids unbounded department aggregation while full details remain available; original Bill_Item ownership protection was preserved (a redundant proposed guard was removed on review); migration readiness marker was moved after all assertions. No new master-demographic snapshots, dispensing or gateway/refund behavior was claimed.

## Functional files changed

**Application:** `app.py`, `hms/__init__.py`, `hms/api.py`, `hms/database.py`, `requirements.txt`, `.env.example`.

**SQL:** fresh01 includes shared corrections; sample02 uses hospital clock; report03 uses ledger/actual receipts; verification04 raises on missing/invalid/disabled objects, constraints and invariants. New `05_integrity_objects.sql`, `06_invariant_checks.sql`, `07_runtime_grants.sql`, `migrations/006_integrity_repair.sql`. Preserved001–005.

**Frontend:** `static/app.js`, `static/styles.css`, `static/index.html`: exact cents, durable retry, metadata editor, ledger reports/print, provenance/time basis, corrected print layout and synthetic notice.

**Tests/tooling:** updated `tests/test_app.py` and `tests/test_oracle_integration.py`; new `tests/test_repairs.py`, `tests/test_http_smoke.py`, `tests/frontend.test.cjs`, `tests/browser_smoke.cjs`, `package.json`, `package-lock.json`; `.gitignore` excludes verification dependencies/results.

**Documentation:** this report, `MIGRATION_RUNBOOK.md`, execution plan, README, PROJECT_REPORT, DEFECT_REGISTER, ER_DIAGRAM, MANUAL_TEST_MATRIX, MANUAL_VERIFICATION_LOG, ROOM_HISTORY_DESIGN; historical headers in DATABASE_MODEL_AUDIT/HOSTILE_AUDIT_REPORT/FRONTEND_DESIGN/FrontEnd preserve earlier evidence without treating it as current.

## Final verification — fresh commands and exact results

Environment: Python3.11 dependencies installed externally in `/tmp/hms-deps`; Node **v22.22.3**; reproducible pinned npm dependencies installed with `npm ci --ignore-scripts --no-audit --no-fund` (success). Large dependencies/browser runtime are not tracked.

| Command / evidence class | Actual result |
|---|---|
| `PYTHONPATH=/tmp/hms-deps python -B -m unittest discover -s tests -v` | **105 tests:86 passed,0 failed,19 skipped.** Breakdown:50 existing fake/API/validation tests +31 repair regressions +3 Oracle safety identity unit tests +2 actual HTTP tests pass;19 opt-in live-Oracle tests skip. |
| `npm test` | **7 mocked-DOM/API tests pass,0 fail/skip.** Exact cents, unpaid controls, durable uncertain retry, complete invoice print, settled notes-only edit, reversal scope, financial report labels. |
| `npm run test:browser` | **HeadlessChrome153.0.8010.0**,9 modules,14 reports,39 intercepted synthetic API calls,0 page errors. CSV export action, request retention across full reload, identical replay payload, print action, print-media y=0,390×844 viewport and exact large cents pass. **No Oracle; not manual E2E.** |
| `node --check static/app.js` | PASS. |
| Python AST + `compile(...)` over app/hms/tests | **9 Python files PASS**, no generated tracked bytecode. |
| Source-only SQL structural review | PASS:14 tables/12 identities/13FK/35 expected trigger names; trigger identifier lengths≤30; shared includes resolve; required trigger names present in verifier; historical001–005 bytes unchanged. **Not an Oracle compiler/parser or live equivalence check.** |
| Actual HTTP smoke | Loopback client to ephemeral Flask server bound0.0.0.0: homepage/assets/config200, honest unconfigured health503; configured auth401 then200. Uses real HTTP/server, no Oracle data. |
| `git diff --check`, branch/HEAD/status review | PASS; same branch/HEAD, no upstream, unstaged/uncommitted repairs, no tracked deletions. |
| Live Oracle/manual matrix | **0 live passes;19 automated tests skipped** because explicit enable/ack and Oracle configuration/service absent. **25 manual scenarios blocked**, not passed. |

Logs (ephemeral, not committed evidence): `/tmp/hms-final-python.log`, `/tmp/hms-final-dom.log`, `/tmp/hms-final-browser.log`. Examined `/tmp/hms-browser-print.png` and `/tmp/hms-browser-mobile.png` are fixture-rendered screenshots, not live patient-data evidence.

## Migration sequence, prerequisites and recovery

Detailed instructions: [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md). Fresh:01 →02 →03 →04 (01 includes05/04/06). Supported existing baseline: only missing001 →002 →003 →004 →005 →006, then03/04. **Never run old migrations atop fresh v6 or rerun a partial corrective installer.** Owner privileges/quota, stopped writers, verified backup and disposable rehearsal are prerequisites. Readiness remains0 until all shared postflight assertions succeed. 006 rejects contradictory legacy data instead of guessing a repair.

DDL autocommits: if anything fails after DDL begins, keep application stopped, capture error/metadata, restore verified backup into a disposable target or rehearse an owner-reviewed forward repair. ROLLBACK does not undo completed DDL. Restricted runtime grants and hospital timezone must be reviewed before resuming; do not grant package/DDL/ANY privileges. Owners/DBAs remain privileged.

## Remaining limits / required lab evidence

1. **Critical certification gap:** compile/execute fresh and upgrade paths on disposable Oracle; compare normalized metadata; test invalid objects, missing guards and partial-DDL recovery. Source-sharing is not executed equivalence.
2. Run19 opt-in tests and25 manual cases, including multirow compound triggers, mixed-operation races/rollback, overpayment/idempotency races, actual former-room histories and restricted runtime privileges. Some higher-combination/multirow scenarios are manual matrix cases, not already automated coverage.
3. No browser→Flask→Oracle persistent E2E, physical print/PDF acceptance, complete accessibility/assistive-technology/device certification or independent reviewer sign-off was performed.
4. Global mutex deliberately caps throughput; direct privileged locks outside protocol can deadlock. Room observations retain server-local time basis; changing server timezone during open legacy stays needs reviewed migration. Legacy payment zones remain UNKNOWN; old month grouping cannot be made exact by invention.
5. Shared phone uniqueness/identity matching, current-master demographic joins, lack of clinical/stock-movement/operator audit and unsupported refunds/gateway settlement are explicit academic limitations, not hidden completed workflows. Basic auth is not production identity/privacy security.

## Review disclosure

A separate **self-review** inspected full tracked diff and new SQL/API/UI/test files, focusing on projection flag cleanup, trigger mutating-table boundaries, statement-vs-row lock order, replay after settlement, money/date encodings, retention-compatible Oracle fixtures, print layout, migration partial failure and runtime grants. Material findings above were corrected and fresh verification rerun. **No independent reviewer or Oracle validator was available.** SQL-specific uncertainty is not downgraded by self-review.

---
## Master continuation — final assessed status (2026-10-29)

### Executive result and boundaries

**Demonstration-ready with stated limitations** for the tested academic environment: personal-role Flask HTTP workflows with persisted **test-only SQLite**, actual Chromium and retained original facts. **Verified for the tested environment** applies to the specific checks below—not an Oracle certification. The Oracle deployment/execution gates are **Blocked**. No live Oracle installation or mutation was attempted. Production clinical/regulatory operation remains out of scope.

The four newly requested correction families are now implemented end-to-end in source/API/role forms/history: consultation/result amendments; remaining-prescription/unperformed-test cancellation; medicine returns/quarantine/stock write-offs/count corrections; financial credits/debits/linked refunds/debt write-offs/controlled invoice voiding. Neither a new login nor a new encounter is presented as a substitute for correction. Original notes, results, instructions, dispensing, invoice sources and receipts survive.

**Latest complete run:**171 Python tests = **145 pass /26 Oracle-gated skips /0 failures**;9 mocked-DOM tests pass; legacy Chromium smoke passes9 modules/14 reports/39 intercepted API calls; **11 actual Flask+on-disk-SQLite Playwright cases pass**. Agent-directed interactive Chromium inspection additionally covered all nine role screens, patient hostile forms/record tampering, mobile navigation/logout and manager dashboard. This is not human-operated clinical acceptance or manual Oracle testing.

### A. Discovery, preservation and method

At master-campaign start: repository `/home/user/DBMS-Project`; branch `arena/92301fba-dbms-project`; full HEAD `2f8b2bb1a6ea2d21a3149a1234a8b866ea3e7cb1`;27 modified tracked files and29 untracked files,0 staged,0 deletions. Baseline rerun143 =120 pass/23 Oracle skips in11.415s. Existing code, canonical report, guide, role fixtures, migrations001–007, actual environment/configuration names and available tools were inspected rather than trusting earlier claims. Initial status was captured in `/tmp/hms-master-initial-status.txt`.

Final observed state: same branch/full HEAD;27 modified tracked files,35 untracked files,0 staged,0 deletions; every starting path remains present. Six new files: `hms/corrections.py`, `tests/test_corrections.py`, additive `008_corrections.sql`, grants10, readiness11 and shared invariants12. Existing guide/report/model/runbook/code/tests were updated in place. Historical001–005 have no Git diff;006/007 were not rewritten during this continuation. No reset/clean/stash/branch switch/commit/push/merge, unrelated deletion, or destructive schema operation was performed. Dependencies, screenshots/PDFs and logs remain ignored or outside Git; bytecode caches are ignored.

Available Superpowers TDD/debugging/verification/review instructions were read from `/tmp/hms-skills`; the actual plugin, subagents and independent reviewer were unavailable. Regression-first engineering and disclosed **self-review** were used—not independent approval. Ruff is a static tool check, not a second human reviewer.

Observed RED→GREEN examples (all expectations retained): six missing corrective endpoints404; receipt replay attempted another insert instead of200; cashier’s bounded original-price return refund403; chart timeline omitted a persisted amendment; patient contact form blanked persisted values; delayed response cleared another action’s UUID;503 after a real committed correction discarded its retry key; successful login #9 was throttled429; early patient result text escaped the same release boundary as its amendment. Tests also cover rollback, over-refunds/returns, expired quarantine, partial cancellation, finance authorization, CSRF/revocation and reporting. Some added boundary/source tests passed immediately and are not claimed as observed RED failures.

Two additional issues were **SQLite adapter defects**, not demonstrated Oracle defects: binary-floating-point aggregates produced a false Partial status for100 exact-cent items; a date-only text clock failed equality with stored midnight dates. The fixture now explicitly emulates the cents/day boundaries; regressions and Chromium were rerun. This adaptation does not certify Oracle NUMBER/DATE semantics. Exploratory visuals prompted deterministic SVG mobile-menu glyphs and hiding empty error bars. A wrong exploratory dashboard selector and reconnect viewport assumption were corrected in the audit driver; they were not reported as application failures.

### B/C. H01–H15 current traceability

“Verified” below means the named non-Oracle environment only. Any Oracle trigger, locking, grants or migration assertion remains blocked until executed.

| ID / cause | Repair / principal files | Actual evidence and final status |
|---|---|---|
| H01 Room/stay projection could bypass Admission | Existing guarded projection package, unified Admission writer, retained stay guards and restricted runtime; `05_integrity_objects.sql`, API, grants07 | Existing repair contracts/gated tests retained; actual inpatient Chromium transfer/discharge preserves room1→2. **Verified fixture; Oracle projection/rollback blocked.** |
| H02 Original billing/status/report arithmetic diverged | One `V_Invoice_Balances`, extended by008 for net charge/cash corrections; API/dashboard/reports/CSV/print use it. Cash-month report uses `V_HMS_Cash_Events`; return review uses original billed unit price | `CorrectionTests` reconciliation:85 billed/50 net collected/35 balance after refund/write-off; all four financial reports/exports; actual browser60→55 and101.02→100. **Verified fixture; Oracle execution blocked.** SQL03 is explicitly gross receipts for v6 compatibility;12 is explicitly net cash. |
| H03 Retry keys could be lost or mistaken for duplicates | Existing normalized payment replay retained; `HMS_Operation` adds actor/action/hash/result journaling; workspace snapshots submitting actor/action, persists payload before send, retains network/5xx uncertainty | Payment DOM/reload smoke; receipt replay; action-switch race fails before fix then passes3 repeats;503 after actual commit replays once after reload. **Verified API/DOM/Chromium; Oracle concurrent uniqueness blocked.** |
| H04 No real Oracle evidence | Safe opt-in suites and individually gated release checklist; no SQLite production fallback | All actual configuration alternatives unset; no SQL*Plus/SQLcl/container/listener tools;26 gated cases skipped. **Blocked**, not repaired by source review. |
| H05 Settled invoice metadata conflicted with edit rules | Immutable issue date/legacy label/ownership; editable notes; original base/items lock after any receipt or corrective history, including full refund; API and008 guards | Existing metadata/DOM checks; full-refund-to-zero regression cannot reopen original item/base edits. **Verified fixture; direct Oracle guards blocked.** |
| H06 Print omitted lines/receipts and broke layout | API related correction history; complete original receipts; explicit INR; print wrapping/fixed widths/page-safe rows; `static/app.js/styles.css` | Short invoice Chromium;100 persisted long lines,2 receipts and refund/price-credit;8-page A4 PDF extracted first/last lines, both receipt references and both correction kinds. **Verified browser/PDF; physical print blocked.** |
| H07 Current room was mislabelled as past history | Retained original admission plus separate observed stays; chart timeline now adds amendments/cancellations/returns/financial events without replacing originals | Existing timeline regressions; patient chart shows original note + amendment, partial dispense + return, room1→2. **Verified fixture; historical Oracle migration observations blocked.** |
| H08 Appointment lifecycle/overlap enforcement differed | Existing half-open doctor/patient overlap and terminal-history guards reused; self-service limited to own future Scheduled booking, same doctor and unchanged duration | Existing unit/lifecycle tests; patient overlap409, foreign-ID404, legal adjacency/reschedule/cancel, terminal reopen409; reception/doctor browser progression. **Verified fixture; raw Oracle lifecycle/races blocked.** |
| H09 Inconsistent lock ordering/unbounded waits | Existing bounded mutex-first transaction; actor refreshed under lock; new append tables use same SQL statement-mutex guards; cumulative SQL checks after statement | Existing order/timeout contracts; serialized SQLite competing refunds give201/409 without over-refund; rollback injection. **Verified application/fixture behavior; real lock/deadlock timing blocked.** Global serialization is deliberate, not hospital-scale throughput. |
| H10 Implicit DDL commits/fresh-upgrade drift | Preserve001–007; additive008 fail-stop preflight, observed cutover, shared12 invariants before marker1, strict11 readiness, restricted grants10 | Source inventory/include/order checks; source-only37 tables/31 identities/66 FKs/92 triggers. **Implemented, Oracle compilation/fresh-upgrade/recovery blocked.** |
| H11 Host timezone/date/unknown history mixed | Existing hospital ZoneInfo/Intl/HMS_Today; new event times UTC; hospital-local chart conversion; original unknown receipt/stay bases remain labelled | Existing midnight/date/timezone tests; schema/health policy; new today-queue fixture regression; monthly report uses original recording month. **Verified application/fixture; Oracle date/timezone behavior blocked.** |
| H12 Floating money/IDs/large totals | Existing Decimal fetch/exact-string serialization/BigInt cents; correction amounts positive/bounded; original-price return budget; monetary fields classified centrally | Existing large/zero/boundary tests; fractional100-line browser invoice; exact reconciliation strings; invalid/over-limit corrections rejected. **Verified tested boundary; Oracle NUMBER metadata/precision blocked.** |
| H13 Destructive “corrections” erased history | No public event mutation/deletion; original retention plus append-only amendment/cancel/stock/financial/operation/cutover guards; grants10 SELECT/INSERT only for events, SELECT only snapshots | API retention/rollback/replay tests and source grant/guard checks; original receipt and clinical texts asserted unchanged. **Verified API/fixture; Oracle direct-DML/grants blocked.** |
| H14 Reports/docs overstated completion/evidence | This canonical report supersedes historical sections; guide, README, migration runbook, extension ER and existing verification records updated | Counts/classes/commands separated; unsupported/blocked list and teacher procedure below. **Updated; no competing final report created.** |
| H15 Shared/demo boundary inadequate for nine users | Personal database-backed roles/sessions/CSRF/scopes/revocation/active staff; secure remote cookies; bounded failed-login throttle, successful commits reset failure budget; `auth.py`, entrypoint and route checks | All nine logins; direct403/404, expired/disabled/revoked/changed account tests, last-manager protection, remote policy; new10-success/8-failure throttle regression. **Verified tested boundary; production privacy/hardening and Oracle runtime grants unverified.** |

### D. Correction semantics and retained effects

The full legal-transition/authorization table is in `MULTIUSER_GUIDE.md` §8. Key decisions:

- Amendments append reason, author and UTC time to a completed encounter or existing result. Treating doctor/manager controls consultation amendments; lab/manager controls results. Patient result and amendment text release together on encounter completion. Original clinical texts remain available beside appendices; no fabricated effective clinical time or signed regulatory attestation is implied.
- Doctor/manager cancels only remaining quantity on a linked Rx, or an Ordered unperformed/unbilled test. Future dispense/result calls reject cancelled orders. Partial dispensing and performed services remain chargeable facts. Cancellation removes genuine unfinished blockers; it does not fabricate completion or erase a clinical order.
- Receipt/return/quarantine/write-off/count events reconcile batch and aggregate stock. Receipt UUID is mandatory; new consignments can reuse a matching medicine/batch/expiry under a distinct legitimate key. Returns are bounded by original unreturned dispense quantity. Only verified in-date restock increases usable stock; quarantine does not. Returns never silently reauthorize further dispensing. Old stock is an observed cutover and unallocated legacy difference, not invented historical receipt/batch provenance.
- Before final billing, actual returned units reduce imported unbilled dispense quantity while source charges remain unchanged; cancelled tests are excluded. After billing, a return appears in review and **requires a separate financial decision**. Manager can credit/write off unpaid value; cashier/manager can refund recorded paid goods up to its uncredited original-price budget. Current catalogue price cannot increase that budget.
- Manager general credit/debit/debt write-off and linked receipt refund append `HMS_Fin_Event`. Refund cash-out and same-value price credit are atomic and explicitly paired; receipts remain original. Original charges stay locked even after a full refund. Cashier cannot grant arbitrary credits/write-offs or unlinked refunds. Void is retained, manager-only, positive unpaid administrative invoices only, with no receipt history; clinical final invoice links are never voided to evade one-final-invoice rules.
- Authoritative net arithmetic: original base+items+debits−credits−refund-price-credits−voids−debt-write-offs; net collected=gross receipts−cash refunds; outstanding=billed−net collected. Dashboard, register, financial reports, CSV and invoice/receipt print reconcile. Monthly cash uses receipt/refund month; debt uses invoice month. No actual card/bank gateway transfer is executed.

### E. Nine role/workspace acceptance matrix

All rows have database-backed personal identity, backend enforcement, live persisted queues and useful actions; this is not login-only delivery. “Browser” is actual Chromium→Flask→test SQLite unless explicitly marked mocked.

| Role | Useful connected work verified | Boundary/correction evidence | Remaining limit |
|---|---|---|---|
| Manager | Staff/account/activation/assignment/configuration; administrative registers and reports; controlled stock/financial corrections | Actual account/staff forms, review/credit/debit/write-off/refund; all-role navigation; direct manager-only checks | No owner-proof database security, advanced approval product or independent review |
| Doctor | Appointed/assigned OP/IP encounter, diagnoses/notes, Rx/test orders, completion/follow-up, retained amendments/cancellation | Actual OP/IP and corrective forms; other-doctor amendment404; new IP work still needs active assignment | Explanatory amendments, not structured regulatory e-signature/effective-time system |
| Patient | Own contacts (persisted prefill), requests, future Scheduled same-doctor reschedule/cancel, released chart/invoices/receipts | Actual self-service/browser print; other-ID404/profile-ID400, unreleased drafts/results hidden | No self-registration, online payment or cancelling checked-in/terminal visits |
| Receptionist | Patient registration, request review/booking/rescheduling, check-in/waiting/cancel/no-show, admission intake | Actual complete OP registration→personal patient linkage→queue; clinical shortcut403 | No clinical decisions or staff/account authority |
| Nurse | Active admission-scoped observations, transfer, discharge, maintenance requests | Actual ward assignment/room1→2/discharge; access revoked after discharge | Admission assignment, not full ward/shift staffing |
| Pharmacist | Catalogue, dated identified receipts/expiry, actual dispensing, return/quarantine/write-off and movement/reconciliation history | Actual receipt/partial dispense/return/write-off; replay/expiry/over-return/stock bounds | Unallocated legacy stock not silently made dispensable; no supplier/disposal logistics |
| Cashier | Care finalization, items while mutable, partial/full payments/receipts, original-price billed-return refund, return-review queue | Actual multiple receipts, prepare-bill blockers/cancellation resolution, bounded refund; arbitrary finance/clinical403 | General corrections/write-offs/voids need manager; no payment gateway |
| Lab | Minimal order/result queue, persisted results and retained result amendments | Actual result/amendment forms; cancelled result rejected; no unrelated chart/finance | No instrument integration or diagnostic interpretation automation |
| Maintenance | Nonclinical room/task queue, reserve/start/complete maintenance | Actual lifecycle/privacy; occupied room rejected; patient/admin endpoints403 | No inventory/procurement scheduling product |

### F. Outpatient / inpatient workflow traceability

| Journey | Persisted links / checked outcomes | Status |
|---|---|---|
| OP registration→request→approval→reschedule→check-in→Waiting | Same Patient and linked personal account; original Appointment identity, doctor and interval rules | Actual Chromium +API verified |
| OP consultation→Rx/tests→dispense/results→completion | Encounter/Appointment, quantity-bearing Rx, batch dispense and care-source charges; patient release boundary | Actual Chromium +API verified |
| OP amendment/cancellation/return→invoice→partial/full receipt/refund | Original facts plus appended correction IDs; cancelled/unperformed charge excluded; partial fulfilment retained; return reviewed at original price;60 gross receipts→55 net after5 goods refund | Actual Chromium +API verified |
| OP follow-up and patient history/print | Follow-up request retains encounter; chart includes original + amendments/returns/cancellation; invoice retains original receipts | Actual Chromium +API verified |
| IP admission→doctor/nurse assignment→observations/care | Existing Admission/Room and scoped personal identities; observations and admission-context encounters | Actual Chromium +API verified |
| IP transfer→discharge→final invoice/receipt | Separate room1→2 stays; open care blocks discharge; access ends after discharge; explicit100 room+20 consultation→120 receipt | Actual Chromium +API verified |
| IP unresolved-order corrections/finalization | Same cancellation/return/net-charge code across admission encounters; exactly one final admission invoice | Shared-domain/API checks; explicit all-family IP corrective UI combination **not separately browser-tested** |
| Any journey on actual Oracle / restricted login | PL/SQL, Decimal/timezone, locks, grants, durable commits/restart | **Blocked**, not inferred from fixtures |

### G. Fresh executed evidence (not combined/fabricated totals)

| Class / command | Result / precise meaning |
|---|---|
| `PYTHONPATH=/tmp/hms-deps python -B -m unittest discover -s tests -v` | **171 =145 pass /26 skip**,27.091s in latest complete run.50 existing API/validation,31 repair,34 personal-role,25 correction/source-contract,2 actual HTTP,3 Oracle-schema-identity safety tests pass.19 prior Oracle +7 role/correction live cases skip. |
| `npm test` | **9 pass**,0 fail/skip,5.912s; mocked DOM/API, not Oracle/browser E2E. Refund scope assertion updated to the newly implemented manager/recorded-return policy—not silently removed. |
| `npm run test:browser` | Chromium153:9 modules/14 reports/**39 intercepted synthetic API calls**,0 page errors; durable payment reload, export/print and390×844 checks pass. Not real workflow data or manual Oracle. |
| `PYTHONPATH=/tmp/hms-deps npm run test:roles` | **11 pass**,40.1s in latest complete run; real Flask HTTP and temporary on-disk SQLite. OP, IP, all nine roles, staff/account forms, maintenance, corrective journey,100-line multi-receipt/refund print/export, action-switch retry race, contact persistence and uncertain503 replay. Deliberately delayed/corrupted transport probes use real captured/committed HTTP responses; ordinary workflow payloads are not mocked. |
| Directed interactive Chromium +visual read | Separate persistent browser session; nine1280×900 role screenshots visually inspected; patient21-char phone validation, escaped hostile contact, overlap409/legal17:30 move, foreign appointment404/profile-ID400, cancellation, restored contacts,390×844 layout/menu and logout401; manager dashboard visually inspected. Maintenance/cashier/lab private chart and accounts403. Automation-driven inspection, **not human physical input or Oracle manual acceptance**. |
| Actual print/PDF | Short invoice and100 long persisted lines with2 receipts and correction pair; multi-page A4 PDF, first/last lines and both references/kinds extracted. Screen and print media inspected; no physical printer used. |
| JS syntax / Python compilation / scoped lint | Both JS app files and browser spec syntax pass;17 Python app/hms/test files compile; `ruff check hms tests --select F,I` passes. This is not a claim of a full-style lint cleanup or Oracle SQL compilation. |
| SQL source review/contracts | Additive includes resolve;7 new tables/4 identities/18 FKs;22 corrective triggers (14 generated mutex/retention +8 domain);16 explicit indexes. Financial self-table/pair/return checks moved to AFTER STATEMENT, not a mutating row trigger. Self-review also found09 counted36 trigger definitions despite a same-name replacement yielding35 distinct objects; observed source-contract RED36!=35, fixed only the verifier, retained007 unchanged. Actual cumulative source count is35 v6+35 role+22 correction=92, not the earlier93 definition-count claim. Source review **does not prove compilation**. |
| Git preservation / diff | `git diff --check` passes; unchanged branch/HEAD;0 staged/deletions; all starting paths retained, no commit/push. |

Logs and visual artifacts are ephemeral `/tmp/hms-master-*` and `/tmp/hms-interactive-*`; they are not committed deliverables or substitutes for reproducible commands. An initial full-browser run exposed the valid-login throttling defect (10/11 passed); it was fixed with observed unit RED→GREEN and the **entire11-case suite rerun successfully**, not hidden by raising timeouts or skipping the test.

### H. Individual Oracle execution outcomes

Actual source configuration alternatives checked without printing secrets: `ORACLE_USER/PASSWORD/DSN/HOST/SERVICE_NAME/SCHEMA` unset, no `.env` (only example); SQL*Plus,SQLcl, Docker,Podman and listener tooling absent. Integration switches and disposable acknowledgment unset. No safe configured target exists. All following remain separate release gates:

| Gate | Outcome / exact reason |
|---|---|
| Fresh clean01+007+008 installation | **Blocked**—no Oracle target/client; no DDL executed |
| Supported001–008 upgrade and populated-data observations | **Blocked**—no confirmed disposable baseline clone |
| Actual columns/identity/FKs/indexes/virtual metadata and PL/SQL compilation | **Blocked**—no USER_* metadata or USER_ERRORS execution |
| Restricted runtime grants/negative privilege checks | **Blocked**—no owner/service logins; grants scripts only source-reviewed |
| Implicit-DDL partial failure and backup/recovery rehearsal | **Blocked**—no explicitly disposable Oracle clone/backup target |
| Transaction rollback of stock/source-charge/correction/audit | **Blocked** on Oracle; SQLite injection passing is not Oracle proof |
| Mutex-first ordering, bounded waits, saturation/deadlock behavior | **Blocked**—no real multi-session lock manager |
| Booking/room/payment/dispense/return/refund/idempotency races | **Blocked**—no Oracle sessions; synthetic serializer is different |
| Exact NUMBER/DATE/TIMESTAMP/timezone semantics | **Blocked**—driver contracts/fixture emulation are not Oracle execution |
| Pool/service restart persistence and fresh-upgrade equivalence | **Blocked**—no actual Oracle data/pool/restart; no metadata comparison |

Safe suites require `HMS_ORACLE_INTEGRATION=1`, additionally `HMS_MULTIUSER_ORACLE_INTEGRATION=1` for seven role cases, and exact `HMS_ORACLE_TEST_ACK=I_CONFIRM_HMS_ORACLE_TEST_IS_DISPOSABLE`. User/session/current schema must match the protected disposable test identity `HMS_ORACLE_TEST`; personal suite requires6/1/1. They retain uniquely named synthetic history, never disable guards or delete original events. Do not point them at personal/production data or weaken the acknowledgment to get green results.

### I. Teacher setup, demonstration and cleanup

1. Use a **confirmed disposable** Oracle12c+ owner schema, backup/export and stop all writers. Read `MIGRATION_RUNBOOK.md`. Fresh:01 → optional synthetic02 →007 →008 →03/04/09/11. Supported existing baseline: only missing001–006, then missing007/008. Do not rerun old installers on fresh schemas or partial DDL.008 includes12 before publishing1; strict11 must show6/1/1 and valid metadata.
2. Provision restricted service login separately; owner applies07,08,10 and verifies actual grants/roles. Configure `.env` locally from example, Oracle owner/current schema and hospital timezone. Install requirements in a local venv; no passwords/default accounts are committed.
3. Run local-console `flask --app app init-manager`. For synthetic demonstration only, optionally `flask --app app create-demo-accounts --ack SYNTHETIC_ONLY`; store generated console credentials privately. Remote/HTTPS requires secure session cookies and no debug. Normal app never substitutes SQLite for missing Oracle.
4. Manager configures fee20, lab test30, medicine5 and verified batch receipt; choose actual IDs from queues. Reception registers/links patient, approves request/books, checks in→Waiting. Doctor consults, orders medicine/test; lab records result/amendment, pharmacy dispenses2. Complete encounter; demonstrate original + amendment and a cancelled unperformed order. Cashier prepares60 invoice, records2×30 receipts. Pharmacy returns1 verified in-date unit; cashier selects its return-review ID and original receipt for5 refund. Show60 gross receipts,55 billed/net collected,0 balance, retained original lines and refund/price-credit pair in print. Never invent a result to unblock billing.
5. IP: admit to available room, assign doctor/nurse, record observation, consult, transfer once, complete care, discharge. Show separate stays and nurse access ending; invoice with explicit100 room charge plus configured care; record/print120 example if only20 consultation. Do not infer historical tariff or effective transfer time.
6. Manager demonstrates a reasoned debit and debt write-off, stock write-off/count correction, forbidden history edits and controlled unpaid **administrative** void. Check both inventory differences0, return-review budget, dashboard/invoice/report/CSV/print agreement. Run commands above; then execute all blocked Oracle gates and human/manual acceptance in the lab before claiming Oracle readiness.
7. Cleanup: log out/revoke demo sessions and close fixture/browser servers; retain synthetic clinical/financial/audit history. Do not delete receipts/events, reset Git, disable guards or run a destructive “cleanup” schema script. Any later discard of an entire dedicated disposable lab schema requires the DBA’s separate confirmed-target procedure/approval. No credentials are stored in Git/chat.

### Remaining limits / honest readiness

- **Blocked:** every Oracle gate above and physical-printer/human-operated clinical acceptance; no Oracle certification claimed.
- **Partially implemented by deliberate academic scope:** explanatory appendices rather than a regulatory e-signature/effective-time/structured amendment product; ward assignments rather than shift scheduling; quarantine records rather than a physical disposal/supplier-return system; advanced date/column filters mainly in manager registers. Primary-queue search does not filter corrective histories; both paginate40 with exact per-scope counts. Full device/assistive-technology certification is not done.
- **Unsupported:** online card/bank refund execution, insurance settlement, automatic historical tariffs/room-night reconstruction, patient self-registration, MFA/SSO/email reset, shared multi-worker throttling or delivered notifications. Unknown legacy stock is not retroactively assigned fabricated batch/expiry history. Requests are reception-reviewed; only future Scheduled bookings permit patient self-change.
- **Security/operations limitation:** synthetic data only. Actor-namespaced browser drafts can contain reasons/clinical text; shared-terminal/local-storage privacy needs production design. Global mutex and global invariant scans limit throughput. App runtime credentials are a trusted service boundary, not an owner-proof per-person Oracle account system; privileged/raw inventory writers can create inconsistencies and must follow/rehearse the supported transaction protocol.
- **Verification limitation:** actual four financial reports/CSV are exercised against persisted fixture data; legacy14-report smoke uses interception. Explicit all-family corrective IP UI combination, real Oracle all-report behavior, physical printing and a genuinely independent review remain unverified. These are not silently counted as passes.

**Conclusion:** the requested missing correction workflows are implemented and demonstrable with stated policies; the tested non-Oracle environment is verified, the academic app is **Demonstration-ready with stated limitations**, and the Oracle deployment claim remains **Blocked** until the individual lab gates pass. This canonical report, not historical phase reports, is the current assessment.
