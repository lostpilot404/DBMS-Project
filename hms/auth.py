"""Database-backed personal identity, fail-closed policy and row ownership.

Application roles do not grant Oracle credentials. All DB access uses the
restricted service login; privileged DB owners remain outside this boundary.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import click
from flask import Blueprint, current_app, g, jsonify, request
from flask.cli import with_appcontext
from werkzeug.security import check_password_hash, generate_password_hash

from .api import (
    ApiError,
    _db,
    _fetch_one,
    _fetch_rows,
    _parse_integer,
    _request_json,
    _transaction,
)

auth = Blueprint("identity", __name__)
ROLES = (
    "manager",
    "doctor",
    "patient",
    "receptionist",
    "nurse",
    "pharmacist",
    "cashier",
    "lab",
    "maintenance",
)
STAFF_ROLES = set(ROLES) - {"doctor", "patient"}
COOKIE = "hms_session"
SESSION_SQL = """SELECT u.user_id,u.username,u.role,u.patient_id,u.doctor_id,u.staff_id,s.csrf_token
FROM HMS_User u JOIN HMS_Session s ON s.user_id=u.user_id LEFT JOIN HMS_Staff st ON st.staff_id=u.staff_id
WHERE s.token_hash=:token AND s.expires_at>:now AND u.is_active='Y' AND (u.staff_id IS NULL OR st.is_active='Y')"""


def now():
    return datetime.now(timezone.utc).replace(
        tzinfo=None
    )  # Oracle TIMESTAMP stores UTC wall time.


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def password_hash(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ApiError("Password must contain 12–128 characters.")
    return generate_password_hash(password, method="scrypt")


def require(*roles):
    if not getattr(g, "user", None):
        raise ApiError("Log in to continue.", 401, "login_required")
    if g.user["role"] not in roles:
        raise ApiError("This role cannot perform that action.", 403, "forbidden")


def patient_scope(alias="p", column="patient_id"):
    """SQL predicate; identifiers only from trusted source, values bound."""
    u = g.user
    role = u["role"]
    col = f"{alias}.{column}"
    if role == "patient":
        return f"{col}=:scope_patient", {"scope_patient": u["patient_id"]}
    if role == "doctor":
        return (
            f"(EXISTS (SELECT 1 FROM Appointment sa WHERE sa.patient_id={col} AND sa.doctor_id=:scope_doctor) OR EXISTS (SELECT 1 FROM HMS_Encounter he WHERE he.patient_id={col} AND he.doctor_id=:scope_doctor) OR EXISTS (SELECT 1 FROM HMS_Care_Assignment ca WHERE ca.patient_id={col} AND ca.doctor_id=:scope_doctor AND ca.is_active='Y'))",
            {"scope_doctor": u["doctor_id"]},
        )
    if role == "nurse":
        return (
            f"EXISTS (SELECT 1 FROM Admission sa JOIN HMS_Ward_Assignment wa ON wa.admission_id=sa.admission_id WHERE sa.patient_id={col} AND sa.discharge_date IS NULL AND wa.user_id=:scope_user AND wa.is_active='Y')",
            {"scope_user": u["user_id"]},
        )
    return "1=1", {}


def check_patient(patient_id, cursor=None):
    if g.user["role"] in ("manager", "receptionist", "cashier"):
        return

    def check(c):
        clause, binds = patient_scope()
        c.execute(
            "SELECT p.patient_id FROM Patient p WHERE p.patient_id=:pid AND " + clause,
            {**binds, "pid": patient_id},
        )
        if c.fetchone() is None:
            raise ApiError("Record not found.", 404, "not_found")

    if cursor is not None:
        check(cursor)
    else:
        with _db().connection() as conn:
            with conn.cursor() as c:
                check(c)


def resource_scope(resource):
    if not current_app.config["AUTH_REQUIRED"] or not getattr(g, "user", None):
        return "1=1", {}
    u = g.user
    r = u["role"]
    if resource == "patients":
        return patient_scope("p")
    if resource == "appointments" and r == "doctor":
        return "a.doctor_id=:scope_doctor", {"scope_doctor": u["doctor_id"]}
    if resource == "appointments" and r == "patient":
        return "a.patient_id=:scope_patient", {"scope_patient": u["patient_id"]}
    if resource in ("admissions", "prescriptions", "bills") and r in (
        "patient",
        "doctor",
        "nurse",
    ):
        return patient_scope(
            {"admissions": "a", "prescriptions": "rx", "bills": "b"}[resource]
        )
    return "1=1", {}


# Explicit endpoint allowlist: an unclassified API endpoint is manager-only.
ACCESS = {
    "receptionist": {
        "patients": "GPI",
        "appointments": "GPI",
        "doctors": "G",
        "departments": "G",
        "admissions": "GP",
        "rooms": "G",
    },
    "doctor": {
        "patients": "G",
        "appointments": "G",
        "prescriptions": "G",
        "admissions": "G",
        "medicines": "G",
    },
    "patient": {
        "patients": "G",
        "appointments": "G",
        "prescriptions": "G",
        "admissions": "G",
        "bills": "G",
        "doctors": "G",
        "departments": "G",
    },
    "nurse": {"patients": "G", "admissions": "GI", "rooms": "G"},
    "pharmacist": {"medicines": "GP"},
    "cashier": {"bills": "GPI", "patients": "G"},
    "lab": {},
    "maintenance": {},
}


def query_one(sql, binds, cursor=None):
    if cursor is not None:
        cursor.execute(sql, binds)
        return cursor.fetchone()
    with _db().connection() as conn:
        with conn.cursor() as c:
            c.execute(sql, binds)
            return c.fetchone()


def authorize_legacy(cursor=None):
    role = g.user["role"]
    endpoint = request.endpoint or ""
    args = request.view_args or {}
    if role == "manager":
        return
    short = endpoint.split(".")[-1]
    if short in ("app_config", "health"):
        return
    if short == "options":
        # The unscoped legacy all-entity dropdown would leak identities.
        raise ApiError("Use the scoped workspace choices.", 403, "forbidden")
    if short in ("patient_summary", "patient_room_history"):
        require("patient", "doctor", "nurse")
        check_patient(args["patient_id"])
        return
    if short in ("bill_ledger",):
        require("cashier", "patient")
        if role == "patient":
            owned = query_one(
                "SELECT patient_id FROM Bill WHERE bill_id=:id",
                {"id": args["bill_id"]},
                cursor,
            )
            if not owned:
                raise ApiError("Record not found.", 404, "not_found")
            check_patient(int(owned[0]), cursor)
        return
    if short in (
        "add_bill_item",
        "bill_item",
        "add_bill_payment",
        "unsupported_reversal",
        "refund_bill",
    ):
        require("cashier")
        return
    if short == "discharge_admission":
        require("nurse")
        owned = query_one(
            "SELECT patient_id FROM Admission WHERE admission_id=:id",
            {"id": args["admission_id"]},
            cursor,
        )
        if not owned:
            raise ApiError("Record not found.", 404, "not_found")
        check_patient(int(owned[0]), cursor)
        return
    if short not in ("collection", "record", "resource_details"):
        raise ApiError("This role cannot use this endpoint.", 403, "forbidden")
    resource = args.get("resource_name")
    if (
        short == "resource_details"
        and resource == "patients"
        and role == "receptionist"
    ):
        raise ApiError(
            "Clinical chart is not available to reception.", 403, "forbidden"
        )
    if short == "resource_details" and resource in (
        "doctors",
        "departments",
        "rooms",
        "medicines",
    ):
        raise ApiError(
            "Linked clinical details are not available through this catalogue.",
            403,
            "forbidden",
        )
    verb = {"GET": "G", "POST": "P", "PUT": "I"}.get(request.method, "D")
    if verb not in ACCESS.get(role, {}).get(resource, ""):
        raise ApiError("This role cannot perform that action.", 403, "forbidden")
    if resource == "patients" and role == "cashier":
        raise ApiError(
            "Use billing patient choices; clinical profiles are not available.",
            403,
            "forbidden",
        )
    rid = args.get("record_id")
    if rid is not None and resource in (
        "patients",
        "appointments",
        "prescriptions",
        "admissions",
        "bills",
    ):
        from .api import RESOURCES

        spec = RESOURCES[resource]
        clause, binds = resource_scope(resource)
        owned = query_one(
            f"SELECT {spec['alias']}.{spec['id']} FROM {spec['table']} {spec['alias']} WHERE {spec['alias']}.{spec['id']}=:rid AND {clause}",
            {**binds, "rid": rid},
            cursor,
        )
        if owned is None:
            raise ApiError("Record not found.", 404, "not_found")
    if request.method == "PUT" and resource == "appointments":
        payload = _request_json()
        if role == "doctor" and (
            set(payload) != {"status"}
            or payload["status"] not in ("In Consultation", "Completed")
        ):
            raise ApiError(
                "Doctors may begin/complete their own consultations only.",
                403,
                "forbidden",
            )
        if (
            role == "receptionist"
            and "status" in payload
            and payload["status"]
            not in ("Checked In", "Waiting", "Cancelled", "No-show")
        ):
            raise ApiError(
                "Reception cannot complete clinical consultations.", 403, "forbidden"
            )
    if resource == "admissions" and request.method == "PUT":
        if set(_request_json()) != {"room_id"}:
            raise ApiError(
                "Nurses may transfer assigned admissions; use the discharge action separately.",
                403,
                "forbidden",
            )
        check_patient_for_admission(rid, cursor)


def check_patient_for_admission(rid, cursor=None):
    owned = query_one(
        "SELECT patient_id FROM Admission WHERE admission_id=:id", {"id": rid}, cursor
    )
    if not owned:
        raise ApiError("Record not found.", 404, "not_found")
    check_patient(int(owned[0]), cursor)


def revalidate_write(c):
    if not current_app.config["AUTH_REQUIRED"] or not getattr(g, "user", None):
        return
    fresh = _fetch_one(
        c, SESSION_SQL, {"token": digest(request.cookies.get(COOKIE, "")), "now": now()}
    )
    if not fresh or fresh["role"] != g.user["role"]:
        raise ApiError("Session changed; log in again.", 401, "login_required")
    g.user = fresh
    if (request.endpoint or "").startswith("api."):
        authorize_legacy(c)


def install(app):
    app.register_blueprint(auth)
    app.extensions["login_attempts"] = defaultdict(deque)
    app.extensions["login_lock"] = threading.Lock()

    @app.before_request
    def identity_boundary():
        if not app.config["AUTH_REQUIRED"]:
            return
        if not request.path.startswith("/api/") or request.path in (
            "/api/auth/login",
            "/api/health",
            "/api/config",
        ):
            return
        token = request.cookies.get(COOKIE, "")
        if not re.fullmatch("[A-Za-z0-9_-]{40,100}", token):
            raise ApiError("Log in to continue.", 401, "login_required")
        with _db().connection() as conn:
            with conn.cursor() as c:
                g.user = _fetch_one(
                    c, SESSION_SQL, {"token": digest(token), "now": now()}
                )
        if not g.user:
            raise ApiError(
                "Session expired or account inactive. Log in again.",
                401,
                "login_required",
            )
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if not secrets.compare_digest(
                request.headers.get("X-CSRF-Token", "").encode(),
                g.user["csrf_token"].encode(),
            ):
                raise ApiError(
                    "Session validation failed. Reload and retry.", 403, "csrf_failed"
                )
        if (request.endpoint or "").startswith("api."):
            authorize_legacy()

    app.cli.add_command(initial_manager)
    app.cli.add_command(demo_accounts)


@auth.post("/api/auth/login")
def login():
    payload = _request_json()
    username = str(payload.get("username", "")).strip().lower()
    password = payload.get("password", "")
    if not isinstance(password, str) or len(password) > 128 or len(username) > 100:
        raise ApiError("Invalid credentials.", 401, "invalid_credentials")
    # Fixed bounded per-process throttle. External shared limiter required for multiple workers.
    key = (request.remote_addr or "", username)
    attempts = current_app.extensions["login_attempts"]
    lock = current_app.extensions["login_lock"]
    with lock:
        q = attempts[key]
        cutoff = time.monotonic() - 300
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= 8:
            raise ApiError(
                "Too many attempts; retry in five minutes.", 429, "rate_limited"
            )
        q.append(time.monotonic())
        if len(attempts) > 10000:
            for old in list(attempts)[:1000]:
                if old != key:
                    attempts.pop(old, None)
    with _transaction(_db()) as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT hospital_timezone,multiuser_version,correction_version FROM HMS_Settings WHERE singleton=1"
            )
            policy = c.fetchone()
            if (
                not policy
                or policy[0] != current_app.config["HOSPITAL_TIMEZONE"]
                or int(policy[1]) != 1
                or int(policy[2]) != 1
            ):
                raise ApiError(
                    "Complete migrations007–008 and align hospital timezone before login.",
                    503,
                    "schema_policy_mismatch",
                )
            u = _fetch_one(
                c,
                "SELECT u.user_id,u.username,u.password_hash,u.role,u.patient_id,u.doctor_id,u.staff_id,u.is_active FROM HMS_User u LEFT JOIN HMS_Staff st ON st.staff_id=u.staff_id WHERE u.username=:username AND (u.staff_id IS NULL OR st.is_active='Y')",
                {"username": username},
            )
            # Dummy hash path avoids fast unknown-user checks.
            encoded = (
                u["password_hash"] if u else current_app.config["DUMMY_PASSWORD_HASH"]
            )
            if (
                not check_password_hash(encoded, password)
                or not u
                or u["is_active"] != "Y"
            ):
                raise ApiError("Invalid credentials.", 401, "invalid_credentials")
            token = secrets.token_urlsafe(48)
            csrf = secrets.token_urlsafe(32)
            c.execute("DELETE FROM HMS_Session WHERE expires_at<=:now", {"now": now()})
            old = request.cookies.get(COOKIE)
            if old:
                c.execute(
                    "DELETE FROM HMS_Session WHERE token_hash=:token",
                    {"token": digest(old)},
                )
            c.execute(
                "INSERT INTO HMS_Session(token_hash,user_id,csrf_token,expires_at) VALUES(:token,:uid,:csrf,:expiry)",
                {
                    "token": digest(token),
                    "uid": u["user_id"],
                    "csrf": csrf,
                    "expiry": now() + timedelta(hours=8),
                },
            )
            audit(c, "login", "user", u["user_id"], u["user_id"])
    # Successful authentication must not consume the failed-attempt budget.
    # Clear only after the session/audit transaction committed successfully.
    with lock:
        attempts.pop(key, None)
    response = jsonify(
        {"data": {"username": u["username"], "role": u["role"], "csrf_token": csrf}}
    )
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        samesite="Lax",
        max_age=8 * 3600,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@auth.get("/api/auth/me")
def me():
    return jsonify({"data": {k: v for k, v in g.user.items() if k != "password_hash"}})


@auth.post("/api/auth/logout")
def logout():
    with _transaction(_db()) as conn:
        with conn.cursor() as c:
            c.execute(
                "DELETE FROM HMS_Session WHERE token_hash=:token",
                {"token": digest(request.cookies.get(COOKIE, ""))},
            )
    r = jsonify({"data": {"logged_out": True}})
    r.delete_cookie(COOKIE)
    return r


@auth.post("/api/auth/password")
def change_password():
    payload = _request_json()
    encoded = password_hash(payload.get("new_password"))
    with _transaction(_db()) as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT password_hash FROM HMS_User WHERE user_id=:id",
                {"id": g.user["user_id"]},
            )
            if not check_password_hash(
                c.fetchone()[0], str(payload.get("current_password", ""))
            ):
                raise ApiError(
                    "Current password is incorrect.", 403, "invalid_credentials"
                )
            c.execute(
                "UPDATE HMS_User SET password_hash=:password WHERE user_id=:id",
                {"password": encoded, "id": g.user["user_id"]},
            )
            c.execute(
                "DELETE FROM HMS_Session WHERE user_id=:id", {"id": g.user["user_id"]}
            )
            audit(c, "password_changed", "user", g.user["user_id"])
    r = jsonify({"data": {"login_required": True}})
    r.delete_cookie(COOKIE)
    return r


def audit(c, action, kind, record_id, actor=None):
    c.execute(
        "INSERT INTO HMS_Audit(user_id,action,entity,record_id) VALUES(:actor,:action,:kind,:rid)",
        {
            "actor": actor or g.user["user_id"],
            "action": action,
            "kind": kind,
            "rid": record_id,
        },
    )


def insert(c, table, values, id_column):
    out = c.var(int)
    cols = ",".join(values)
    params = ",".join(":" + k for k in values)
    c.execute(
        f"INSERT INTO {table}({cols}) VALUES({params}) RETURNING {id_column} INTO :out_id",
        {**values, "out_id": out},
    )
    v = out.getvalue()
    return int(v[0] if isinstance(v, list) else v)


def account_values(payload, creating=True):
    allowed = {
        "username",
        "password",
        "role",
        "patient_id",
        "doctor_id",
        "staff_id",
        "is_active",
    }
    if set(payload) - allowed:
        raise ApiError("Unknown account field.")
    values = dict(payload)
    if creating:
        username = str(values.get("username", "")).strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._@-]{2,99}", username):
            raise ApiError("Username must be 3–100 simple characters.")
        values["username"] = username
    elif "username" in values:
        raise ApiError("Username is immutable.")
    if "password" in values:
        values["password_hash"] = password_hash(values.pop("password"))
    elif creating:
        raise ApiError("Password required.")
    if creating:
        values.setdefault("is_active", "Y")
    if values.get("is_active", "Y") not in ("Y", "N"):
        raise ApiError("is_active must be Y or N.")
    if creating or "role" in values:
        role = values.get("role")
        if role not in ROLES:
            raise ApiError("Choose a supported role.")
        links = {k: values.get(k) for k in ("patient_id", "doctor_id", "staff_id")}
        required = (
            "patient_id"
            if role == "patient"
            else "doctor_id"
            if role == "doctor"
            else "staff_id"
        )
        if not links[required] or any(v for k, v in links.items() if k != required):
            raise ApiError(
                "Role requires exactly its matching patient, doctor or staff link."
            )
        for k, v in links.items():
            values[k] = _parse_integer(v, k, minimum=1) if v else None
    elif set(values) & {"patient_id", "doctor_id", "staff_id"}:
        raise ApiError("Change role and its complete links together.")
    return values


@auth.route("/api/admin/users", methods=["GET", "POST"])
@auth.route("/api/admin/users/<int:uid>", methods=["PUT"])
def users(uid=None):
    require("manager")
    if request.method == "GET":
        with _db().connection() as conn:
            with conn.cursor() as c:
                c.execute(
                    "SELECT user_id,username,role,patient_id,doctor_id,staff_id,is_active FROM HMS_User ORDER BY username"
                )
                rows = _fetch_rows(c)
        return jsonify({"data": rows})
    values = account_values(_request_json(), uid is None)
    with _transaction(_db()) as conn:
        with conn.cursor() as c:
            for field in ("username", "patient_id", "doctor_id", "staff_id"):
                if values.get(field) is not None:
                    c.execute(
                        f"SELECT COUNT(*) FROM HMS_User WHERE {field}=:value AND user_id<>:id",
                        {"value": values[field], "id": uid or 0},
                    )
                    if c.fetchone()[0]:
                        raise ApiError(
                            "An account already uses this username or linked identity.",
                            409,
                            "account_conflict",
                        )
            if uid is not None:
                c.execute(
                    "SELECT u.role,u.is_active,s.is_active,u.staff_id FROM HMS_User u LEFT JOIN HMS_Staff s ON s.staff_id=u.staff_id WHERE u.user_id=:id",
                    {"id": uid},
                )
                old = c.fetchone()
                if not old:
                    raise ApiError("Account not found.", 404, "not_found")
                was_capable_manager = (
                    old[0] == "manager" and old[1] == "Y" and old[2] == "Y"
                )
                remains_capable = (
                    values.get("role", old[0]) == "manager"
                    and values.get("is_active", old[1]) == "Y"
                )
                if was_capable_manager and remains_capable:
                    c.execute(
                        "SELECT is_active FROM HMS_Staff WHERE staff_id=:id",
                        {"id": values.get("staff_id", old[3])},
                    )
                    target_staff = c.fetchone()
                    remains_capable = bool(target_staff and target_staff[0] == "Y")
                if was_capable_manager and not remains_capable:
                    c.execute(
                        "SELECT COUNT(*) FROM HMS_User u JOIN HMS_Staff s ON s.staff_id=u.staff_id WHERE u.role='manager' AND u.is_active='Y' AND s.is_active='Y'"
                    )
                    if c.fetchone()[0] <= 1:
                        raise ApiError(
                            "Cannot remove the last active manager.",
                            409,
                            "last_manager",
                        )
                if not values:
                    raise ApiError("No changes supplied.")
                c.execute(
                    "UPDATE HMS_User SET "
                    + ",".join(k + "=:" + k for k in values)
                    + " WHERE user_id=:id",
                    {**values, "id": uid},
                )
                c.execute("DELETE FROM HMS_Session WHERE user_id=:id", {"id": uid})
            else:
                uid = insert(c, "HMS_User", values, "user_id")
            audit(c, "account_changed", "user", uid)
    return jsonify({"data": {"id": uid}}), 201 if request.method == "POST" else 200


@click.command("init-manager")
@click.option("--username", prompt=True)
@click.password_option(confirmation_prompt=True)
@with_appcontext
def initial_manager(username, password):
    """Local console only, serialized one-time initial manager creation."""
    with _transaction(_db()) as conn:
        with conn.cursor() as c:
            c.execute("SELECT COUNT(*) FROM HMS_User")
            if c.fetchone()[0]:
                raise click.ClickException(
                    "Accounts exist. Ask an active manager; bootstrap refused."
                )
            sid = insert(
                c,
                "HMS_Staff",
                {"full_name": "Initial manager", "staff_kind": "manager"},
                "staff_id",
            )
            uid = insert(
                c,
                "HMS_User",
                account_values(
                    {
                        "username": username,
                        "password": password,
                        "role": "manager",
                        "staff_id": sid,
                    }
                ),
                "user_id",
            )
            audit(c, "bootstrap", "user", uid, uid)
    click.echo(
        "Manager created. Log in with your chosen credentials; no default password exists."
    )


@click.command("create-demo-accounts")
@click.option("--ack", required=True, help="Must equal SYNTHETIC_ONLY")
@with_appcontext
def demo_accounts(ack):
    """Generate separate disposable demo credentials; never hardcoded passwords."""
    if ack != "SYNTHETIC_ONLY":
        raise click.ClickException("Explicit SYNTHETIC_ONLY acknowledgement required.")
    # Console credentials deliberately printed only AFTER successful commit.
    credentials = []
    suffix = secrets.token_hex(3)
    with _transaction(_db()) as conn:
        with conn.cursor() as c:
            c.execute(
                "SELECT COUNT(*) FROM HMS_User u JOIN HMS_Staff s ON s.staff_id=u.staff_id WHERE u.role='manager' AND u.is_active='Y' AND s.is_active='Y'"
            )
            if not c.fetchone()[0]:
                raise click.ClickException("Initialize a manager first.")
            dep = insert(
                c,
                "Department",
                {"department_name": "Demo " + suffix, "location": "Synthetic demo"},
                "department_id",
            )
            pid = insert(
                c,
                "Patient",
                {
                    "patient_name": "Synthetic patient " + suffix,
                    "date_of_birth": datetime(2000, 1, 1),
                    "gender": "O",
                },
                "patient_id",
            )
            did = insert(
                c,
                "Doctor",
                {
                    "doctor_name": "Synthetic doctor " + suffix,
                    "specialization": "Demo",
                    "department_id": dep,
                },
                "doctor_id",
            )
            for role in ROLES:
                password = secrets.token_urlsafe(18)
                username = f"{role}.{suffix}"
                link = (
                    {"patient_id": pid}
                    if role == "patient"
                    else {"doctor_id": did}
                    if role == "doctor"
                    else {
                        "staff_id": insert(
                            c,
                            "HMS_Staff",
                            {"full_name": role + " " + suffix, "staff_kind": role},
                            "staff_id",
                        )
                    }
                )
                uid = insert(
                    c,
                    "HMS_User",
                    account_values(
                        {
                            "username": username,
                            "password": password,
                            "role": role,
                            **link,
                        }
                    ),
                    "user_id",
                )
                audit(c, "demo_created", "user", uid, uid)
                credentials.append((username, password))
    for username, password in credentials:
        click.echo(f"{username}\t{password}")
