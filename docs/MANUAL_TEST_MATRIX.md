# v6 manual Oracle acceptance matrix

**None of these live/manual cases were executed here.** All 25 are BLOCKED on disposable Oracle; PASS0, FAIL0, BLOCKED25. Real Chromium fixture automation is separate and now available; it is not a manual/live-Oracle pass. See [campaign evidence](REPAIR_CAMPAIGN.md).

Prerequisites: exact disposable HMS_ORACLE_TEST identity/acknowledgement, fresh v6 or rehearsed upgrade001–006, executable04 assertions pass, synthetic fixtures P1/P2/D1/D2/R1/R2/M1, two sessions for races, API/DB hospital timezone match. Record request IDs, redacted SQL/errors, row counts and reload results. No important database. History remains; do not disable guards for cleanup.

| ID | Actions | Expected committed state after refresh/re-query | Status |
|---|---|---|---|
| M01 | Create/edit/search department; duplicate name; attach doctor; delete parent. | Unique name; complete details and count; bounded preview; referenced delete blocked. | BLOCKED |
| M02 | Create doctor with department/contact; edit; filters/sort/page; bad FK/duplicate contact. | Valid rows persist; invalid relationship/contact rejected. | BLOCKED |
| M03 | Register/edit/search patient; future DOB/invalid gender/oversize input. | Correct day/contact state; invalid data rejected. Duplicate identity is not auto-merged. | BLOCKED |
| M04 | Delete patient with visits/bills. | FK protects retained history; no cascade loss. | BLOCKED |
| M05 | Book D1/P1 09:00 duration30; 09:15 conflict; 09:30 adjacency. | Doctor AND patient half-open interval checks; adjacency succeeds. | BLOCKED |
| M06 | Two simultaneous overlapping bookings, different starts; cancel winner/rebook. | One active winner; loser conflict; cancelled history retained and slot released. | BLOCKED |
| M07 | Full queue lifecycle; invalid skips; check-in wrong day; overdue No-show. | Valid transitions persist; terminal history locked; date rules hospital-local. | BLOCKED |
| M08 | Direct SQL status+booking change; multivisit INSERT/UPDATE; cross-doctor same-patient overlap. | Combined edits and both-resource overlaps rejected atomically. | BLOCKED |
| M09 | Create Available rooms; admit P1; race P2 for same room. | One active occupant/admission; Room Occupied; loser no partial changes. | BLOCKED |
| M10 | Transfer R1→R2; inspect patient, admission, former-room details/report. | Prior observation retained; R1 free/R2 occupied; original admission not relabelled R2. | BLOCKED |
| M11 | Discharge; repeat/reopen/backdate/future attempts. | Valid release closes current observation; forbidden rewrites rejected. | BLOCKED |
| M12 | Direct Room Occupied/Available bypass and direct stay INSERT/UPDATE/DELETE. | Guard rejection; no occupancy/observation contradiction. Owner/DBA is privileged. | BLOCKED |
| M13 | Roll back transfer/discharge; mixed Room/Admission/master operations from two sessions. | All projections restored; bounded conflicts; no silent partial commit. | BLOCKED |
| M14 | Inspect migrated LEGACY stays; unknown earlier transfers. | Unknown intervals/provenance shown; no invented start/transfer or original room. | BLOCKED |
| M15 | Medicine create/edit/low-stock/search; concurrent atomic decrement. | No negative count/lost update; stock is not dispensing history. | BLOCKED |
| M16 | Create/edit prescription with related IDs; delete/reassign patient; inspect medicine history. | Order saved without decrementing stock; forbidden ownership/delete blocked. | BLOCKED |
| M17 | Create base bill + several items; edit/remove unpaid item; max quantity/line/invoice. | Exact cents and correct limit rejections; no overflow/float loss. | BLOCKED |
| M18 | Record partial then full payments; overpay; negative/zero payment. | Paid/balance and receipt counts agree; invalid payments roll back. | BLOCKED |
| M19 | Lose payment response; close/reload and retry original even when fully settled. | Same persisted UUID/material request; same receipt ID, no second charge. | BLOCKED |
| M20 | Same-key same/different payload, cross-bill and concurrent replay. | Matching200/original ID; changed409; exactly one receipt. | BLOCKED |
| M21 | Post-payment edit notes/date/label/charges; move item to another bill; refund/delete. | Only notes allowed; ownership/settled charges/retention enforced; reversal clearly unsupported. | BLOCKED |
| M22 | Compare dashboard, register, ledger, chart, four financial reports, CSV, printed invoice. | Exact same billed/paid/balance; legacy Paid never receipt; zero invoice Paid without receipt. | BLOCKED |
| M23 | Run14 reports with filters/pages; export full filtered data; formula-prefixed names. | Same filter semantics, full export independent of page, safe CSV text. Receipt/invoice months distinct. | BLOCKED |
| M24 | Test hospital midnight vs UTC/browser zone; DB/API mismatch; physical print. | Day policy consistent, mismatch readiness503; timestamp precision retained; invoice begins first print page. | BLOCKED |
| M25 | Fresh install vs001–006 upgrade; malformed data; partial DDL; runtime-user grants/auth. | Fail-fast assertions, equivalent metadata; safe reviewed recovery; no package/owner privileges; unauthorized401. | BLOCKED |
