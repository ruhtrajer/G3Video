#!/usr/bin/env python3
import os
from app.server import app

if __name__ == "__main__":
    host = os.getenv("G3VIDEO_HOST", "0.0.0.0")
    port = int(os.getenv("G3VIDEO_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true")
    print(f"G3Video server starting on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
