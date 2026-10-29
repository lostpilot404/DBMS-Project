"""Actual HTTP/Flask smoke, deliberately without Oracle; not persisted E2E."""

import threading
import unittest
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from werkzeug.serving import make_server

from hms import create_app
from hms.database import OracleDatabase


@contextmanager
def serving(config=None, app=None):
    app = app or create_app(
        database=OracleDatabase(),
        test_config={"TESTING": True, "AUTH_REQUIRED": False, **(config or {})},
    )
    server = make_server("0.0.0.0", 0, app)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()


class ActualHttpSmokeTests(unittest.TestCase):
    def test_assets_policy_and_honest_no_database_state(self):
        with serving() as base:
            for path in (
                "/",
                "/static/app.js",
                "/static/styles.css",
                "/favicon.ico",
                "/api/config",
            ):
                with self.subTest(path=path), urlopen(base + path, timeout=5) as r:
                    self.assertEqual(r.status, 200)
                    self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
            with self.assertRaises(HTTPError) as error:
                urlopen(base + "/api/health", timeout=5)
            self.assertEqual(error.exception.code, 503)
            self.assertIn(b"database_unavailable", error.exception.read())

    def test_configured_auth_guards_actual_http(self):
        with serving(
            {"DEMO_USERNAME": "demo", "DEMO_PASSWORD": "synthetic-test"}
        ) as base:
            with self.assertRaises(HTTPError) as error:
                urlopen(base + "/api/config", timeout=5)
            self.assertEqual(error.exception.code, 401)
            request = Request(
                base + "/api/config",
                headers={"Authorization": "Basic ZGVtbzpzeW50aGV0aWMtdGVzdA=="},
            )
            with urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)

    def test_explicit_sqlite_fixture_is_labelled_without_changing_normal_app(self):
        import tempfile
        from pathlib import Path

        from tests.role_fixture import RoleDatabase
        from tests.role_http_fixture import fixture_app

        with tempfile.TemporaryDirectory(prefix="hms-fixture-label-") as directory:
            database = RoleDatabase(str(Path(directory) / "fixture.sqlite"))
            with serving(app=fixture_app(database)) as base:
                with urlopen(base + "/", timeout=5) as response:
                    body = response.read().decode()
                    self.assertIn("SQLite test fixture", body)
                    self.assertIn("Not Oracle", body)
                    self.assertIn("data-fixture-mode", body)
            database.sql.close()
        with serving() as base:
            with urlopen(base + "/", timeout=5) as response:
                self.assertNotIn("data-fixture-mode", response.read().decode())
