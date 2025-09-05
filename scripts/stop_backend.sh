#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/Hackathon/zone_detection/backend"
PY="/usr/bin/python3"

pkill -f "$PY -u $APP_DIR/app.py" || true
echo "Backend gestoppt (falls es lief)."


