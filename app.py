"""Local development entry point. Run with `python app.py`."""
import os

from dotenv import load_dotenv

from hms import create_app

load_dotenv()
app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
    host = os.getenv("HMS_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost", "::1"} and not (app.config["AUTH_REQUIRED"] and app.config["SESSION_COOKIE_SECURE"]):
        raise RuntimeError("Remote binding requires HMS_COOKIE_SECURE=true and personal authentication behind HTTPS. Shared Basic auth is only an additional boundary.")
    if host not in {"127.0.0.1", "localhost", "::1"} and debug:
        raise RuntimeError("Do not expose the development debugger on a remote interface.")
    app.run(host=host, port=port, debug=debug)
