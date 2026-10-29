# HMS full repair implementation plan and execution ledger

> Historical v6 execution ledger, retained for traceability. Its no-commit/no-cleanup constraint and unsupported-refund statements were superseded by the master/release campaigns. Current status and commands: [canonical report](../../REPAIR_CAMPAIGN.md) and [guide](../../MULTIUSER_GUIDE.md).

Goal: repair H01–H15 and integrate the academic Oracle/Flask/JS workflows.
Constraints: preserve migration 001–005; no commits/push/reset/cleanup; synthetic data only.
Method: published Superpowers instructions read; actual plugin/subagent tool unavailable.
Specification: user full repair campaign and Audit 1 findings in session.
Architecture: bounded global write mutex (academic throughput tradeoff), guarded room/history projections, shared invoice view, exact money strings, replayable payments, hospital-local dates. Schema owner is privileged; restricted runtime user is the supported deployment boundary. No fabricated payments/history. Refunds/reversals are explicitly unsupported.

## Ordered tasks / acceptance
- [x] T1 Baseline, failing regression harness (H04). Run existing suite, test capabilities; add Python/DOM/SQL contract regressions. Real Oracle tests remain separately opt-in.
- [x] T2 Database boundary (H01,H08,H09,H10,H11,H13): fresh SQL and corrective 006; mutex before row locks, internal projection guard, retention, patient/doctor intervals, dates, pre/postflight assertions. Direct DML/rollback/race tests.
- [x] T3 Financial contract (H02,H03,H05,H12): shared view, decimal strings, request replay/mismatch, immutable date/status, notes-only metadata after payment. Test replay before balance check and rollback.
- [x] T4 Integration (H06,H07): ledger-backed invoice/receipt print, assignment-aware patient/room history, refresh and exact frontend formatting; durable pending request across reopen/reload. DOM regressions.
- [x] T5 Scope/security/workflows (H15): local binding, configurable remote Basic auth boundary, no real-data claims, prescription != dispense, all advertised controls/routes checked.
- [x] T6 Documentation/migration runbook/evidence (H14): current README/report/ER/manual matrix and archived audits distinguished; supported migration recovery.
- [x] T7 Full verification and separate self-review: no reviewer tool available. Fix material findings; record actual pass/skip counts and full diff review. Oracle/browser evidence strictly distinguished.

## Review focus
Projection guard exception cleanup; compound-trigger mutating table behavior; mixed-operation lock order; lost-response replay after full settlement; legacy Paid labels never create transactions; exact cents at large values; date boundaries; migration partial DDL and restricted runtime grants.

## Evidence ledger
Baseline: clean arena/92301fba-dbms-project at 2f8b2bb1a6ea2d21a3149a1234a8b866ea3e7cb1; no upstream. No Oracle variables/client/container/browser executable found.


## Completion / blocked certification (2026-10-29)
Implementation tasks T1–T7 completed with a separate self-review; this does NOT mark live Oracle acceptance complete. Actual Superpowers plugin/subagent/reviewer unavailable. Baseline66=53pass/13skip; initial repair18tests/19expected assertion failures. Added focused RED→GREEN regressions and integrated every subsystem.

Fresh final Python105=86pass/19Oracle skips/0fail; DOM7/7; real Chromium153 fixture smoke9modules/14reports/39mock calls/0page errors; print layout first failed y602 then fixed y0. Actual HTTP2 tests pass without Oracle. JS syntax,9-file Python AST/compile, source SQL inventory/includes/unchanged001–005 and diff whitespace checks pass. Node22.22.3/pinned npm install verified. Full result and exact boundaries: `docs/REPAIR_CAMPAIGN.md`.

**Blocked:** Oracle compilation, fresh/upgrade metadata equivalence, direct SQL/multirow/mixed-lock/concurrency/rollback/runtime-user proof, persistent browser→Flask→Oracle E2E, physical printing and25manual cases.19Oracle tests skipped, not passed. No commit/push/merge/reset/clean/stash/history operation; same branch and HEAD, work remains unstaged/uncommitted.
