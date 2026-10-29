"""Flask application factory and safe API error handling."""
from __future__ import annotations

import logging
import os
import re
import secrets
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from .api import ApiError, api
from .database import DatabaseNotConfigured, OracleDatabase

ROOT = Path(__file__).resolve().parent.parent
_DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_urlsafe(32))


def create_app(database: Any | None = None, test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")
    app.config.from_mapping(
        AUTH_REQUIRED=os.getenv("HMS_AUTH_REQUIRED", "true").lower() != "false",
        SESSION_COOKIE_SECURE=os.getenv("HMS_COOKIE_SECURE", "false").lower() == "true",
        DUMMY_PASSWORD_HASH=_DUMMY_PASSWORD_HASH,
        HOSPITAL_TIMEZONE=os.getenv("HOSPITAL_TIMEZONE", "Asia/Kolkata"),
        DEMO_USERNAME=os.getenv("DEMO_USERNAME", ""), DEMO_PASSWORD=os.getenv("DEMO_PASSWORD", ""),
        MAX_CONTENT_LENGTH=32 * 1024,
        JSON_SORT_KEYS=False,
        PROPAGATE_EXCEPTIONS=False,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config['AUTH_REQUIRED'] and not app.testing:
        raise ValueError('AUTH_REQUIRED=False is restricted to explicit test harnesses.')
    ZoneInfo(app.config["HOSPITAL_TIMEZONE"])  # fail startup for invalid policy
    if bool(app.config["DEMO_USERNAME"]) != bool(app.config["DEMO_PASSWORD"]):
        raise ValueError("Configure both DEMO_USERNAME and DEMO_PASSWORD, or neither when using personal authentication.")

    @app.before_request
    def demo_boundary():
        if app.config["DEMO_PASSWORD"]:
            auth = request.authorization
            if not auth or not secrets.compare_digest((auth.username or "").encode(), app.config["DEMO_USERNAME"].encode()) or not secrets.compare_digest((auth.password or "").encode(), app.config["DEMO_PASSWORD"].encode()):
                return jsonify({"error": {"code":"authentication_required", "message":"Demo access requires authentication."}}), 401, {"WWW-Authenticate": 'Basic realm="HMS synthetic demo"'}

    app.extensions["hms_database"] = database or OracleDatabase.from_environment()
    app.register_blueprint(api)
    from .auth import install
    install(app)
    from .workflows import work
    app.register_blueprint(work)
    from .corrections import corrections
    app.register_blueprint(corrections)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/favicon.ico")
    def favicon():
        return send_from_directory(app.static_folder, "favicon.svg", mimetype="image/svg+xml")

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify({"error": {"code": error.code, "message": error.message}}), error.status

    @app.errorhandler(DatabaseNotConfigured)
    def handle_database_configuration(error: DatabaseNotConfigured):
        # Configuration details and credentials are intentionally not sent to the browser.
        return jsonify({"error": {
            "code": "database_unavailable",
            "message": "Oracle is not configured or could not be reached. Check the local .env settings and database service.",
        }}), 503

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        if isinstance(error, HTTPException):
            return jsonify({"error": {
                "code": error.name.lower().replace(" ", "_"),
                "message": error.description,
            }}), error.code

        error_text = str(error).upper()
        if any(code in error_text for code in ("DPY-6001", "DPY-6005", "DPY-4011", "DPI-1047")):
            app.logger.warning("Oracle driver connection error (%s)", error_text.split(":", 1)[0])
            return _error("database_unavailable", "Oracle could not be reached. Check the database service and connection settings.", 503)

        oracle_code = _oracle_code(error)
        if oracle_code is not None:
            app.logger.warning("Oracle request failed (ORA-%05d)", oracle_code)
            if oracle_code in (54, 60, 30006):
                return _error("resource_busy", "The scheduling resource is busy. Please retry.", 409)
            if oracle_code == 1:
                return _error("conflict", "A record with one of these unique values already exists.", 409)
            if oracle_code in (2292,):
                return _error("record_in_use", "This record is referenced by other records and cannot be deleted.", 409)
            if oracle_code in (2291, 1400, 2290, 1438, 12899):
                return _error("constraint_violation", "The submitted values do not satisfy a database relationship or constraint.", 400)
            if oracle_code == 20010:
                return _error("invalid_discharge_date", "Discharge date cannot be earlier than the admission date.", 400)
            if oracle_code == 20014:
                return _error("active_admission", "Discharge the patient before changing or removing an active admission.", 409)
            if oracle_code == 20019:
                return _error("patient_ownership_immutable", "Patient ownership cannot be changed when editing this record.", 409)
            if oracle_code == 20020:
                return _error("appointment_history", "Completed, cancelled, and no-show appointment history cannot be edited.", 409)
            if oracle_code == 20022:
                return _error("appointment_in_past", "A scheduled appointment cannot be in the past.", 400)
            if oracle_code == 20023:
                return _error("invalid_appointment_start", "New appointments must start as Scheduled.", 400)
            if oracle_code == 20024:
                return _error("invalid_status_transition", "The requested appointment state transition or booking edit is not allowed.", 409)
            if oracle_code == 20025:
                return _error("appointment_not_today", "Patients can be checked in only on the appointment date.", 409)
            if oracle_code == 20026:
                return _error("appointment_not_overdue", "An appointment can be marked No-show only after its date has passed.", 409)
            if oracle_code == 20027:
                return _error("admission_history", "The requested admission transition is not allowed.", 409)
            if oracle_code == 20028:
                return _error("room_history_inconsistent", "The room assignment history is inconsistent; no changes were saved.", 409)
            if oracle_code == 20029:
                return _error("invalid_admission_date", "Admission and discharge dates cannot be in the future.", 400)
            if oracle_code == 20030:
                return _error("appointment_overlap", "This doctor already has an overlapping appointment.", 409)
            if oracle_code == 20031:
                return _error("invoice_has_payments", "Invoice charges cannot be changed after payment.", 409)
            if oracle_code == 20032:
                return _error("payment_history", "Payment history cannot be changed or deleted.", 409)
            if oracle_code == 20033:
                return _error("overpayment", "Payment exceeds the outstanding balance.", 409)
            if oracle_code in (20040, 20042, 20043):
                return _error("history_or_projection_guard", "Retained history and derived state cannot be changed directly.", 409)
            if oracle_code in (20201,20202,20203,20204,20210,20211,20212,20213):
                return _error('care_integrity', 'Care history, stock, identity or finalization rule prevents this change.',409)
            if oracle_code in (20041, 20044):
                return _error("invalid_date_or_total", "Date or amount exceeds the supported policy.", 400)
            if oracle_code in (20011, 20012, 20013):
                return _error("room_unavailable", "That room is not available for this operation.", 409)
            if oracle_code in (942, 904):
                return _error("schema_upgrade_required", "Database schema is not ready; complete the documented migrations.", 503)
            if oracle_code in (3113, 3114, 12170, 12514, 12541, 12545, 12547):
                return _error("database_unavailable", "Oracle could not be reached. Check the database service and connection settings.", 503)

        app.logger.exception("Unhandled application error", exc_info=error)
        return _error("internal_error", "The request could not be completed. Check the application log and try again.", 500)

    @app.after_request
    def add_security_headers(response):
        if request.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        return response

    if not app.testing:
        logging.basicConfig(level=logging.INFO)
    return app


def _oracle_code(error: Exception) -> int | None:
    for argument in getattr(error, "args", ()):
        code = getattr(argument, "code", None)
        if isinstance(code, int):
            return code
    match = re.search(r"ORA-(\d{5})", str(error))
    return int(match.group(1)) if match else None


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message}}), status
