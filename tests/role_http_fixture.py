"""Test-only HTTP server with SQLite compatibility data; never import in app."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flask import request
from werkzeug.serving import run_simple

from hms import create_app
from tests.role_fixture import RoleDatabase


def fixture_app(db):
    """Explicit disposable demo only; production create_app never falls back here."""
    app = create_app(
        database=db,
        test_config={
            "TESTING": True,
            "AUTH_REQUIRED": True,
            "SESSION_COOKIE_SECURE": False,  # Test-only loopback HTTP server.
            "DEMO_USERNAME": "",
            "DEMO_PASSWORD": "",
        },
    )

    @app.after_request
    def label_fixture(response):
        if request.path == "/" and response.mimetype == "text/html":
            response.direct_passthrough = False
            response.headers["Cache-Control"] = "no-store"
            response.headers.pop("ETag", None)
            response.headers.pop("Last-Modified", None)
            html = response.get_data(as_text=True)
            html = html.replace("<title>", "<title>SQLite test fixture · ", 1)
            html = html.replace(
                "</header>",
                '</header><aside data-fixture-mode role="note" class="work-alert">SQLite test fixture · Not Oracle · Synthetic records only · Resets when stopped</aside>',
                1,
            )
            response.set_data(html)
        return response

    return app


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="hms-role-browser-") as directory:
        db = RoleDatabase(str(Path(directory) / "fixture.sqlite"))
        app = fixture_app(db)
        run_simple(
            "0.0.0.0",
            int(os.environ.get("HMS_TEST_PORT", "5037")),
            app,
            use_reloader=False,
            threaded=True,
        )
