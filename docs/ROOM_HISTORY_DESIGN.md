# Room history — v6 implementation status

Admission is authoritative. Shared installer `sql/05_integrity_objects.sql` guards Room and Admission_Room_Stay, maintains observations atomically via a private-state package, retains history and takes the global write mutex first. Migration002 preserves legacy snapshots with unknown intervals;006 installs corrective guards without inventing prior transfers. Patient timelines no longer relabel the admission's original room using current room_id; room details query immutable stay rows to find former occupants. Recording timestamps are server-local observations, not recovered clinical effective times. Runtime is not granted package execution; owners/DBAs remain privileged. Oracle compilation, race and rollback proof remains pending.

[Runbook](MIGRATION_RUNBOOK.md), [current defects](DEFECT_REGISTER.md), [campaign evidence](REPAIR_CAMPAIGN.md).

---

> **Historical design below:** superseded proposals/limitations are retained for provenance, not current implementation status. In particular direct projection bypasses and “not implemented” financial/room-history statements below describe an earlier snapshot.

# Room history implementation note

The historical design below predates the current code. `Admission_Room_Stay`, the admission history trigger, admission-detail view, patient history endpoint, report, and `sql/migrations/002_room_history.sql` are now implemented but **not executed or verified on Oracle**. Migration records one legacy snapshot with unknown times per existing admission; the previous rooms cannot be recovered. New timestamps represent database recording time, not effective historical time. The existing Room and Admission columns remain synchronized through triggers during normal Admission mutations; direct Room/history DML can bypass consistency and remains unresolved. See README for safety and migration instructions.

---

# Room-assignment history: design and migration draft (not applied)

`Admission.room_id` is the only stored room, and PUT `/api/admissions/<id>` overwrites it. Existing trigger synchronization updates Room status but records neither prior room nor transfer time. A legitimate transfer loses the prior value. This remains an open P1; the current UI's room transfer **does not** preserve room-stay history. No Oracle implementation of this design is included or claimed.

## Proposed relation
A future `AdmissionRoomStay` has generated `stay_id` PK, non-null FK `admission_id` and `room_id`, nullable `started_at` and `ended_at` TIMESTAMP, non-null `recorded_at` TIMESTAMP DEFAULT SYSTIMESTAMP, and a non-null `source` constrained to `LIVE` or `MIGRATED_SNAPSHOT`. `LIVE` rows require `started_at`; dates have `ended_at >= started_at` when both known. A virtual active admission key `CASE WHEN ended_at IS NULL AND source = 'LIVE' THEN admission_id END` unique prevents two active live stays for one admission; a corresponding active room key prevents two live stays in a room. An explicit `is_current`/ended-state distinction is needed for migrated snapshots because an unknown historical end is not an open stay. Add indexes on admission and room FKs. These constraints are a design, not tested DDL.

## Data-preserving migration draft (do not execute as SQL)
1. Quiesce all writers; back up and rehearse on a disposable copy. Check active-room and active-patient duplicates, mismatched Room status, and Oracle object/trigger validity. Resolve discrepancies manually before proceeding.
2. Create the relation and indexes non-destructively. For each admission add exactly one `MIGRATED_SNAPSHOT` referring to its currently stored `room_id`; both actual room start and end remain unknown. Preserve `admission_date` and `discharge_date` on Admission, not as invented transfer times. For an active admission create a *separate* current observation with an explicit unknown start and current/open flag; refine constraints to cover current migrated rows. Do not manufacture a move from the snapshot to that same room. For discharged admissions, leave the snapshot historical. Store a clear provenance and timestamp of migration observation. This is a draft requiring a finalized representation that avoids duplicating a single assignment before DDL is written.
3. In one transaction, lock Admission and the destination Room (and establish a deterministic lock order for old/new rooms to reduce deadlocks), validate active state and destination availability, close the current room-stay at server timestamp, insert the new stay, change `Admission.room_id`, and synchronize both room statuses. On discharge close current stay in the same transaction. A date-only discharge can be backdated; keep transaction/recorded timestamps distinct from effective dates rather than asserting an invented discharge time. Add guard triggers or a single database package and revoke direct writes so API and direct writers cannot bypass the ledger.
4. Replace current history screens, reports, patient timeline and CSV joins with explicit stay entries; distinguish the snapshot's unknown interval. Keep existing room_id as current/last assignment until all reads have migrated. Update API, frontend, test cleanup, ER and seed data together.
5. Verify trigger compilation, deterministic lock ordering, same-room no-op, concurrent allocations/transfers/discharge, rollback, migrated active/closed histories, old schema compatibility, report reconciliation, and two-session tests on Oracle. DDL commits implicitly: migration is not atomic; define restart/recovery steps and never imply `ROLLBACK` reverses DDL.

## Other normalized workflow assessments
- `Encounter` + `Diagnosis`: useful for consultation notes/diagnoses linked to patient and clinician; must define appointment/admission linkage and ownership rules before implementation. No clinical conclusions are supplied.
- Prescription header + items: needed for multi-medicine prescriptions. Current rows represent one medicine and existing rows can each migrate to a one-item header. Dispensing is separate.
- Medicine batches + stock movements: required for expiry-aware inventory and traceable receipts/issues/dispensing; do not fabricate historical movements from current balances. An opening balance must be explicitly identified as such.
- Invoice lines + payments: current Bill has only three editable aggregate charges and a Paid/Pending label. It cannot represent multiple service quantities, payment dates, partial settlements or refunds. Migration could turn each nonzero charge into a labeled legacy line with quantity one and original charge; preserve zero-valued components if needed to reconcile. Do **not** fabricate a payment event from `Paid`: it is an unverified status, not receipt evidence. A real implementation must add payment records, transactional balance/overpayment rules, UI and revised reports together. The assignment report is missing and the applicable requirements cannot be independently confirmed.

These structures are not implemented, and no sample rows, reports or UI currently use them. They need schema/API/frontend design and actual Oracle verification before being enabled.
