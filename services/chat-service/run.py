#!/usr/bin/env python3
"""
Development runner for Chat Service (Phase 2).
Starts the Flask app on the requested port.
"""
import os
from app.main import create_app


def main():
    port = int(os.environ.get("PORT", 8000))
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()


