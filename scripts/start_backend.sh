#!/usr/bin/env bash
set -euo pipefail

# Verzeichnisse dynamisch relativ zum Skript bestimmen
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${ROOT_DIR}/backend"
LOG_FILE="${APP_DIR}/backend.log"

# Python auf PATH, fallback auf /usr/bin/python3
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY="/usr/bin/python3"
fi

# Standard: echte Kamera erlauben, Dummy aus (kann vom Nutzer überschrieben werden)
export REQUIRE_REAL_CAMERA="${REQUIRE_REAL_CAMERA:-1}"
export USE_DUMMY_CAMERA="${USE_DUMMY_CAMERA:-0}"

mkdir -p "${APP_DIR}"
cd "${APP_DIR}"

# Vorherigen Prozess stoppen (falls vorhanden)
pkill -f "${PY} -u ${APP_DIR}/app.py" || true

# Starten
nohup "${PY}" -u "${APP_DIR}/app.py" >> "${LOG_FILE}" 2>&1 &

# Warten bis Health-Check OK ist
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:5000/healthz >/dev/null; then
    echo "Backend läuft auf Port 5000."
    exit 0
  fi
  sleep 0.5
done

echo "Backend startete nicht erfolgreich. Letzte Logs:" >&2
tail -n 100 "${LOG_FILE}" || true
exit 1


