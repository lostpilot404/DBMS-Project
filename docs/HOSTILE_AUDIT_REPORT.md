# Hostile audit report

## Baseline and scope
2026-10-28: `/home/user/DBMS-Project`, branch `arena/fec8be83-dbms-project`, clean at start, HEAD `5db998c9c2205baee51e3718bd724a7a3aba28a2`; origin `https://github.com/lostpilot404/DBMS-Project.git`. One reachable local commit; `git cat-file -t 2623e5fcfe781d7fa06d7202c9d9d5a4b525675f` failed; `git ls-remote origin` showed main and fix branch at baseline plus PR 1 at another SHA, not the requested SHA. This does not prove absence among unreachable remote objects. Prior frontend and bill-date API, UI max, test are present (`static/app.js`, `hms/api.py`, `tests/test_app.py`). No untracked files at baseline. `R1.pdf` is absent; earlier documentation claims its contents but is secondary evidence only. No independent assignment instructions were found. Do not present those secondary claims as verified mandates.

## Plan and approach
Read source and DDL before changes; trace routes and SQL, rank defects, reproduce safe client-side/API behavior with synthetic values, fix a narrowly verifiable bypass, run tests, document unavailable live checks. The matrix contains the remaining concrete live plan. This is an incomplete audit, not a comprehensive certification: all nine tables were inspected statically, not all UI controls or execution paths manually exercised.

## Requirement traceability
`R` = README/PROJECT_REPORT claim, not independently verified assignment. `U` = user-provided original nine entities; `I` = implemented functionality, `A` = additional realistic requirement, not established as mandated.

| Capability / source | Table, route, screen | Expected / method | Actual / status |
|---|---|---|---|
| Nine core entities / U, R | nine tables, `/api/<resource>` and screens | tables and FK relationships; inspect DDL | all declared; Oracle creation NOT TESTED |
| 3NF / R | all tables | inspect dependencies, derived values | simplistic proof contradicted by anomalies; PARTIAL |
| master patient/doctor/department / I | Patient, Doctor, Department; resource screens | CRUD and FK restrictions | statically present; live behavior NOT TESTED |
| appointment lifecycle and exact slots / I | Appointment, guard trigger, queue | transition/uniqueness/concurrency | declared, only test doubles run; Oracle NOT TESTED |
| admission and room state / I | Room, Admission, three triggers, discharge/transfer | occupancy atomicity and history | transfer history lost; direct DML holes; FAIL for complete history, live concurrency NOT TESTED |
| prescriptions vs stock / I | Medicine, Prescription, stock-adjustments | order does not deduct stock | implementation separate; real transaction NOT TESTED |
| bill calculation / I | Bill virtual total, bill screen | sum charges, valid date | declared, date tested with doubles; Oracle NOT TESTED |
| reports and CSV / I | 12 API reports; `sql/03` views; Reports | independently reconcile filtered totals/export | source reviewed; known dataset reconciliation NOT TESTED; paid flag not actual receipts |
| actual clinical encounter/diagnosis / A | absent | link clinician, patient and clinical data if required | absent; mandate unknown, NOT TESTED as assignment |
| authentication/RBAC/audit / production need | absent | protect sensitive data and changes | FAIL for real use; outside demonstrated academic scope |

## Implementation map and evidence
`app.py` starts Flask; `hms/database.py` lazy pooled python-oracledb Thin connections, `hms/__init__.py` app/error handling; `hms/api.py` whitelisted resource definitions, report SQL, routes, validation, transactions. `static/index.html`, `static/app.js`, `static/styles.css` implement frontend. `sql/01` creates nine tables, appointment and admission triggers; `02` relative-date fictional seeds, `03` views and reports, `04` dictionary checks. `tests/test_app.py` uses fakes; `tests/test_oracle_integration.py` guards a dedicated schema and is opt-in. `docs/ER_DIAGRAM.mmd`, `PROJECT_REPORT.md`, `MANUAL_VERIFICATION_LOG.md`, `FRONTEND_DESIGN.md`, `FrontEnd.md` are prior documentation, not independent proof.

SQL uses bind parameters for data and resource allowlists for identifiers; CSV text cells escape formula prefixes, but spreadsheets vary and no actual import tested. Generic errors are sanitized, debug is opt-in, CSP/frame/nosniff headers are configured, and no CORS configuration was found. Lack of access control remains critical; use only synthetic data on a controlled network. No legal compliance claim is made; jurisdiction and applicable authoritative requirements must be assessed before deployment.

## Tests and limitations
Clean dependency setup: `python -m venv .venv`, `.venv/bin/pip install -r requirements.txt`; `.venv/bin/python -m unittest discover -s tests -v`: 47 tests, 40 passed and 7 skipped; skips are live Oracle integration, not passes. `node --check static/app.js` and Python compileall succeeded. Before installing dependencies, unittest failed to import Flask/oracledb. A direct test-client experiment with `FakeDatabase` reproduced D04 (201, INSERT with future discharge) and D02 (200, UPDATE reassignment); D04 now rejected before DB by regression test. Fake output proves application branch only. No SQL script, trigger, database transaction, report dataset or concurrency operation was executed against Oracle; no Oracle service, credentials, SQL*Plus or container runtime were available. No browser executable was available, so no interactive, responsive, print, accessibility or screenshots evidence is claimed.

Use README disposable-schema safeguards exactly; inspect scripts, backup nothing by connecting to an important schema, run 01–04 only on new `HMS_ORACLE_TEST`, review `USER_ERRORS`, metadata and test output. Oracle DDL commits implicitly, even where SQL*Plus says ROLLBACK. Reconcile reports with independent expected rows and run two-session races before acceptance. A schema migration has not been attempted; see model audit and defects.

## Continuation (current worktree)

The checkout is shallow (`.git/shallow` contains baseline HEAD), so its parent ancestry is not locally available. The requested earlier `2623e5f` object is absent locally and not advertised by remote refs; its precise four changes cannot be compared without that object. Future bill-date validation, its unit test and frontend improvements exist in the current tree; do not overwrite current files with an unverified older copy. Obtain the commit or patch from its original environment and review a targeted diff before integrating.

Follow-up fixed API patient-ownership edits for bills/prescriptions and declared corresponding Oracle triggers in the fresh schema and upgrade script. The migration has NOT been executed; its compilation and behavior are not verified. `tests/test_app.py` reproduces the prior unsafe path using fakes and verifies rejection of attempted ownership edits, allowed edits and admission failure handling. Test suite: 52 total, 44 passed, 8 skipped (all live Oracle integration). The admission transfer still loses previous room; the [design draft](ROOM_HISTORY_DESIGN.md) is not an implemented workflow. No end-to-end browser/Oracle or real report reconciliation has occurred. The original audit's pre-continuation results above remain historical, not current test counts.
