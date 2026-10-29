# Oracle v6 installation, upgrade and recovery

**Status: implemented SQL, not executed/compiled against Oracle in this campaign.** Oracle12c+, dedicated synthetic-data schema only. These instructions are not certification of a safe production upgrade.

## Prerequisites

1. Freeze API, seed scripts, jobs and every direct writer. Take and verify a restorable backup/export. Rehearse on a disposable clone first. Use owner with CREATE TABLE, VIEW, TRIGGER, PROCEDURE privileges, identity support and tablespace quota.
2. Inventory actual tables/columns/constraints/triggers and `USER_ERRORS`; do not infer migration state from a README. 001–005 are unchanged historical files. Supported old nine-table baseline must already have the documented lifecycle status/unique-active constraints; other versions need explicit reconciliation.
3. Review legacy duration policy (003 sets 30 minutes, **not recovered duration**) and 002 observations (unknown old intervals, **not recovered transfers**). No script invents receipts from labels.

## Fresh path

Run `@sql/01_create_schema.sql`, 02, 03, 04 using SQL*Plus/SQLcl from repository root. 01 includes 05 (corrective objects) and 06 (invariants); **do not separately rerun these installers**. 04 uses WHENEVER SQLERROR and raises on broken invariants, missing/disabled/invalid objects or wrong version. Keep all writers stopped until seed/reports/verification complete.

## Existing baseline path

Run only migrations whose objects are absent, in order:

1. `001_patient_ownership.sql`
2. `002_room_history.sql`
3. `003_appointment_duration.sql`
4. `004_appointment_overlap.sql`
5. `005_bill_ledger.sql`
6. `006_integrity_repair.sql`
7. `@sql/03_useful_queries.sql`, `@sql/04_verification.sql`

A database already at 001–005 starts at 006. Fresh v6 does not run any migrations. Shared `@@` includes resolve relative to their containing script. Do not copy individual SQL fragments into an arbitrary current directory.

006 checks twelve business tables, duration, valid objects, enabled/validated constraints, no v6 marker, then the executable data invariants **before DDL**. It rejects inconsistent occupancy/history, duplicate active assignments, patient/doctor overlap, overpayments/oversized amounts, future clinical dates and non-midnight date-only values. Stop and review source records on failure; do not truncate dates, discard rows, rewrite receipts or invent transfers automatically. Unknown historical timestamp zones remain unknown.

006 installs the **same** 05 definitions used by fresh 01: mutex/settings, exact invoice view, notes/time-basis field, bounded line/total checks, write locks, projection/retention/lifecycle guards, clock and FK indexes. Postflight checks object compilation and data, then version 6. Running 04 independently also verifies required triggers/constraints. Review `USER_ERRORS` even if a CREATE TRIGGER returned only a warning.

## Failure and recovery

- **Preflight failure before any DDL:** no corrective objects should exist. Transaction is rolled back, but diagnose actual state. Resolve conflicts through an explicit reviewed correction/data-retention policy, then rehearse again.
- **Failure during/after DDL:** earlier DDL may already be committed; version 0 or missing/partial objects are **not success**. Leave application stopped. Capture SQL*Plus exit code/output, USER_ERRORS, USER_OBJECTS/CONSTRAINTS/TRIGGERS and a schema export. Restore the verified backup into a disposable target, or prepare and rehearse an owner-reviewed forward repair. **Never blindly rerun 006**, reset the repository, drop history, disable runtime guards or resume against a partially installed schema.
- Verify all executable assertions, compare fresh-vs-upgrade metadata in separate disposable schemas (normalized types/defaults/constraints/indexes/triggers/views/functions/packages), run the opt-in tests, then manual matrix. This equivalence and lock/rollback testing remain **unverified here**.

## Runtime and timezone

Provision a separate login with CREATE SESSION only; owner runs `07_runtime_grants.sql`. Set ORACLE_SCHEMA to owner. Runtime gets selected DML, history SELECT, invoice view/settings SELECT, mutex locking, HMS_Today execution; **not HMS_Internal or DDL/ANY roles**. Inspect actual grants/roles: the script cannot revoke pre-existing broad roles. Owner/DBA remains privileged.

Initial clinical-day policy: Asia/Kolkata. Configure API to match HMS_Settings; readiness rejects mismatches. New payment timestamps UTC; old payment zones `LEGACY_UNKNOWN`, grouped by stored legacy calendar month when exact conversion is impossible. Room observations retain server-local timestamps; they are not effective historical clinical times. Changing Oracle server timezone while legacy stays are open requires a separate reviewed timestamp migration.

All supported direct writers take `SELECT mutex_id FROM HMS_Write_Mutex WHERE mutex_id=1 FOR UPDATE WAIT 5` **before any explicit entity locks**, hold to commit/rollback. Statement triggers do this for ordinary DML. Manual owner row locks without the protocol can still create deadlocks; 409 retry handling is not proof deadlocks cannot happen. Global serialization deliberately limits throughput.

## Additive007 multi-user extension (not executed here)

The v6 procedure above is retained. The default personal-account app now additionally requires007; health/login reject absent marker or timezone mismatch. Fresh01 is v6: apply007 once after v6 assertions. Existing supported baselines apply only missing001–006, then007. Do not rerun001–006 on a fresh schema, or007 on an already/partly extended schema.

1. Keep all writers stopped; rehearse and back up a **disposable** schema. Capture preflight04/USER_ERRORS and an export.007 checks v6 marker, absent extension objects/marker column, valid baseline objects and executable v6 invariants **before DDL**.
2. Run `@sql/migrations/007_multiuser.sql` as owner. New marker column starts0; no credentials or inferred history are inserted. DDL creates16 extension tables,35 FKs,15 identity columns and35 distinct triggers in addition to retained v6 objects; adds clinical links/quantity to Prescription and Bill. Counts are source inventory, **not executed Oracle metadata**.
3. Run03,04 and `@sql/09_multiuser_verification.sql`; inspect USER_ERRORS and actual constraints/indexes/triggers. Marker must be schema6 / multiuser1.09 checks extension table/guard/index inventories and ownership, quantities, test/result, batch and charge/invoice invariants. Empty accounts before bootstrap are legitimate. Confirm fresh/upgrade metadata equivalence on separate disposable schemas.
4. Provision restricted service login separately. Owner runs07 and `08_multiuser_grants.sql`. Runtime must have no account/history DELETE, no audit/result/dispense UPDATE, no DDL/ANY/broad role or HMS_Internal. HMS_Session cleanup is the intentional DELETE exception. Verify existing grants and required column-level consultation_fee UPDATE; setting current schema is not a grant.
5. At local console run `flask --app app init-manager`, then optionally generated synthetic demo accounts. Set secure-cookie flag for HTTPS/remote use. See [personal-account guide](MULTIUSER_GUIDE.md).
6. Run existing opt-in Oracle tests plus `tests.test_multiuser_oracle` with both integration switches/ack. Confirm actual authentication, isolation, clinical care, stock rollback/concurrent dispensing, ward transfer/final invoice, restart persistence and restricted-runtime operation. Compare exact receipts/stock/charge links after retries. New tests create unique retained synthetic records, never disable guards/drop tables for cleanup.

**007 failure:** completed DDL may already be committed. Leave the application stopped; capture exit status/output and metadata. Do not blindly rerun, delete history, set the marker manually or disable guards. Restore a verified backup into a rehearsal target or prepare an owner-reviewed forward repair. Unverified here: Oracle compilation of defaults/compound and row triggers, implicit-commit failure boundaries, NUMBER/DATE/TIMESTAMP behavior, new FK/index/grant effectiveness, mutex/revalidation lock order, batch and source-charge atomic rollback, real races, fresh-vs-upgrade equivalence and actual Oracle persistence.

## Additive008 corrective-event extension — current personal app prerequisite

The007 instructions above are historical baseline instructions; the current default app requires **6 / multiuser1 / correction1**. Fresh:01 → optional02 →007 →008 →03/04/09/11. Upgrade only missing001–006, then missing007/008; a verified007 starts at008. Never rerun historical installers or apply source fragments to live patient data.

1. Stop **every** writer, export/back up, confirm a disposable rehearsal schema. Capture v6/007 postflights and metadata before DDL.008 checks v6/007 marker, invalid baseline objects, absent correction marker and batch totals not exceeding aggregate before adding anything. It invokes09; contradictory facts require investigation, not automated deletion.
2. Owner runs `@sql/migrations/008_corrections.sql`. Seven tables add4 identities and18 FKs;22 new triggers and16 explicit indexes; five support views plus replacement authoritative invoice view. Source-only cumulative inventory:37 tables /31 identities /66 FKs /92 triggers. These counts are **not Oracle metadata evidence**.
3. The marker starts0. Snapshot available quantities per existing batch, unallocated legacy aggregate difference and max existing dispense ID; these are **migration observations**, never reconstructed receipt/expiry/dispense history. Original clinical/payment facts and001–007 definitions remain retained. No fresh seed invents prior corrective events.
4.008 installs immutable-event/mutex guards and post-statement cumulative bounds (avoiding mutating-table queries), then includes shared read-only `12_correction_invariants.sql` **before** publishing marker1. It commits only after assertions, then runs strict readiness wrapper11. Independently rerun04,09,11; review USER_ERRORS, constraints, indexes, generated IDs, original/net invoice and inventory arithmetic.11 refuses marker0, even if an interrupted installer happened to create all objects.
5. Owner applies grants07 +08 + **10_corrections_grants.sql** to the separate restricted login. New events receive SELECT/INSERT only; cutover snapshots/views SELECT only. Verify actual grants, column grants, roles, public grants, ownership and current schema. No DDL, ANY, HMS_Internal, event UPDATE/DELETE or snapshot DML. Service credentials are not personal end-user credentials. Owner/DBA remains privileged; unsupported raw inventory DML can create a mismatch and is not a replacement for the API transaction protocol.
6. Configure environment and bootstrap as described in MULTIUSER_GUIDE. Health/login require correction1 and aligned hospital timezone. Rehearse complete UI/API flows and scoped direct requests as runtime, then opt-in Oracle suites. The seven role/correction Oracle cases require both integration switches and the exact disposable-schema acknowledgment;19 prior Oracle cases remain separate. Unacknowledged/default runs **skip**, never fall back to SQLite.

**008 failure:** DDL already completed may be committed. Stop; capture SQL*Plus exit status/log and USER_ERRORS/OBJECTS/TRIGGERS/CONSTRAINTS/INDEXES/settings. Do not rerun008, set its marker manually, overwrite cutover snapshots, alter old events, disable guards, or resume writers. Restore the verified backup into a disposable rehearsal schema or prepare an owner-reviewed forward recovery. Rollback cannot undo Oracle DDL. There is no destructive cleanup script.

**Disposable-lab release gates:** execute fresh and supported-upgrade paths separately; compare normalized columns/defaults/identity/virtual metadata/FKs/checks/indexes/views/triggers/packages/functions, not generated system names. Intentionally fail an installation on a **disposable clone**, verify fail-stop/backup recovery; never rehearse failure against retained data. Verify restricted grants positively and negatively; parallel booking/room transfer/payment/dispense/return/refund/key races and timeout/rollback; close/reopen pool and restart service against the same Oracle data. Capture original receipts/notes, corrective links and stock differences before/after. Every one of these Oracle execution gates remains blocked in this sandbox, not passed by source or SQLite checks.

## Release rehearsal mode / reset boundary

See MULTIUSER_GUIDE §10 for the explicit test-only SQLite HTTP rehearsal. Its page is visibly labelled **Not Oracle**, its known passwords are synthetic only, and its temporary database resets on stopping/restarting that separate fixture process. This does not alter the normal Oracle entrypoint or authorize clearing a valuable Oracle schema. No automated destructive Oracle reset is supplied. Real Oracle release gates above remain mandatory.
