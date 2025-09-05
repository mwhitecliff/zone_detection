#!/usr/bin/env bash
set -euo pipefail

# Verzeichnisse dynamisch relativ zum Skript bestimmen
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${ROOT_DIR}/backend"

# Python auf PATH, fallback auf /usr/bin/python3
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY="/usr/bin/python3"
fi

pkill -f "${PY} -u ${APP_DIR}/app.py" || true
echo "Backend gestoppt (falls es lief)."


