#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/Hackathon/zone_detection/backend"
LOG_FILE="/Hackathon/zone_detection/backend/backend.log"
PY="/usr/bin/python3"

# Echte Kamera erzwingen
export REQUIRE_REAL_CAMERA=1
export USE_DUMMY_CAMERA=0

cd "$APP_DIR"

# Vorherigen Prozess stoppen (falls vorhanden)
pkill -f "$PY -u $APP_DIR/app.py" || true

nohup "$PY" -u "$APP_DIR/app.py" >> "$LOG_FILE" 2>&1 &

# Warten bis Health-Check OK ist
for i in {1..30}; do
  if curl -fsS http://127.0.0.1:5000/healthz >/dev/null; then
    echo "Backend läuft auf Port 5000."
    exit 0
  fi
  sleep 0.5
done

echo "Backend startete nicht erfolgreich. Letzte Logs:" >&2
tail -n 100 "$LOG_FILE" || true
exit 1


