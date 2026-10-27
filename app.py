"""Local development entry point. Run with `python app.py`."""
import os

from dotenv import load_dotenv

from hms import create_app

load_dotenv()
app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").strip().lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug)
