# Current defect register — repair campaign 2026-10-29

Status **implemented** means code and stated non-Oracle regressions exist, not live Oracle certification. H04 remains blocked. The master continuation in the canonical report supersedes the v6-only evidence/counts below;008 adds retained corrective events,171 Python tests/26 Oracle skips and11 actual role-browser cases. [Full evidence](REPAIR_CAMPAIGN.md), [runbook](MIGRATION_RUNBOOK.md), [manual matrix](MANUAL_TEST_MATRIX.md).

| Finding | Status and repair | Regression / outstanding proof |
|---|---|---|
| H01 Direct Room/history bypass | Implemented: guarded projections, private internal state, unified Admission writer, restricted grants. | SQL contracts; opt-in projection/transfer rollback tests. Live trigger compilation/rollback pending. |
| H02 Financial disagreement | Implemented: shared invoice view, ledger dashboard/register/history/reports/SQL/CSV. Legacy labels never receipts. | Shared-query tests, zero-invoice test, browser fixture print. Live cross-surface totals pending. |
| H03 Duplicate-key != replay; UI loses key | Implemented: normalized matching replay before balance check; mismatches409; localStorage request survives close/reload. | Fake replay/mismatch/cross-bill; DOM and real Chromium lost-response retry; opt-in concurrent replay. |
| H04 No Oracle evidence | **BLOCKED, not fixed:** no Oracle configured/service. Nineteen opt-in tests are separately gated. | SQL source checks cannot certify Oracle. |
| H05 Post-payment metadata/edit conflict | Implemented: immutable issue date/legacy label; notes editable; settled UI omits charges; item ownership immutable. | API/DOM metadata regressions; SQL guard review. |
| H06 Incomplete print | Implemented: item/receipt columns, actual paid/balance, legacy disclaimer; print CSS removes hidden page layout. | DOM plus Chromium print-media top-position regression; physical printing pending. |
| H07 Mislabelled room histories | Implemented: original Admission event does not infer current room; separate unknown legacy observations; former rooms found through stay rows. | Timeline regression; source/detail-query review. Actual migrated history pending. |
| H08 SQL lifecycle weaker than API | Implemented: SQL combined booking/status rejection and patient+doctor interval checks. | Source contracts; opt-in direct SQL and cross-doctor patient tests. |
| H09 Lock inversion/unmapped deadlock | Implemented mitigation: global mutex first on API and SQL statements, WAIT5, ORA54/60/30006 →409. | Raw first-lock regression; opt-in concurrency. Arbitrary privileged row locks still outside protocol. |
| H10 Non-fatal migration verification | Implemented: 006 preflight, shared fresh/upgrade objects, executable assertions and missing/invalid/disabled-object checks. | File/source tests; actual DDL/recovery/equivalence pending. |
| H11 Clocks/date precision | Implemented: hospital-zone days in Python/JS/SQL, readiness policy match, timestamp-preserving observations, explicit UTC/legacy time basis. | Midnight/format/config tests. Oracle timezone execution pending. |
| H12 Decimal→float | Implemented: Decimal fetch, string money encoding, bounded arithmetic, BigInt cents. | Exact large-cent and zero/ID encodings; browser exact formatting. |
| H13 Direct SQL history deletion | Implemented: retained clinical/financial/observation triggers and runtime grants. | Source guard tests; opt-in direct SQL retention. |
| H14 Stale docs | Updated README, report, ER, matrix, audit headers, runbook and final evidence. | Source review; old audit material labelled historical, no stale count treated as current. |
| H15 Unrestricted remote exposure | Implemented academic boundary: loopback default, configured Basic auth, remote bind refusal without credentials, synthetic-only notices. | Unauthorized/authorized API tests. Not enterprise/real-PHI security. |

## Additional review findings and deliberate limits

- Department LISTAGG preview is bounded to five names (avoids unbounded Oracle string aggregation); full details retained. Regression added before repair.
- Print hidden app layout originally pushed invoice below first page; observed in real Chromium, failing layout regression then CSS fix.
- Item bill reassignment is forbidden to prevent moving a paid line to an unpaid invoice. Existing SQL ownership guard preserved; live execution pending.
- Patient identity/deduplication and household phone policy remain assignment limitations, not automatically “repaired.” Master-name/department joins are current context, not immutable snapshots.
- Prescription dispensing, audited inventory movements, encounter/diagnosis, roles/operator audit, refunds and real gateway settlement are not advertised as implemented. Retention does not mean all mutable clinical corrections are audited.
- Samples are same-day repeat-safe only, not concurrent seeds or reset scripts. Migration failures require reviewed recovery, not deleting data. VARCHAR2 byte semantics and Oracle version-specific compilation require lab verification.
