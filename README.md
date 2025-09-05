# Zone Detection – Raspberry Pi AI Cam

Ein leichtgewichtiges Tool, um auf einem Raspberry Pi einen Live‑Videostream anzuzeigen, Zonen (Bereiche) im Bild per Maus zu markieren und diese Zonen im Backend zu speichern. Ideal, um später KI‑Modelle oder Logik auf definierte „Safe/Warning/Error“-Zonen anzuwenden.

## Features
- MJPEG‑Livestream vom Pi (Fallback auf Dummy‑Stream ohne Kamera)
- Interaktive Annotation im Browser: Rechtecke zeichnen, Kategorien wählen (safe/warning/error)
- Speicherung der Zonen als Pixelkoordinaten in `backend/regions.json`
- Einfache REST‑Schnittstellen: `GET/POST /regions`, `GET /video_feed`, `GET /healthz`

## Projektstruktur
- `backend/`: Flask‑App, Kamera‑Abstraktion und Region‑Speicher
  - `app.py`: API‑Server und Routen
  - `camera.py`: Zugriff auf `picamera2` mit Dummy‑Fallback
  - `regions_store.py`: Thread‑sicheres JSON‑Speicher‑Modul
  - `regions.json`: Persistente Ablage der Regionen
  - `requirements.txt`: Python‑Abhängigkeiten
- `frontend/`: Statisches UI
  - `index.html`: Oberfläche für Stream und Annotation
  - `static/app.js`, `static/styles.css`: Logik und Styles
- `scripts/`: Hilfsskripte zum Starten/Stoppen
  - `start_backend.sh`, `stop_backend.sh`
- `Makefile`: Optionaler Einstiegspunkt für typische Tasks

## Voraussetzungen
- Raspberry Pi OS (Bullseye oder neuer empfohlen)
- Python 3.9+ (System‑Python auf dem Pi ist ausreichend)
- Kamera: `picamera2` kompatible Pi‑Kamera ODER Verwendung des Dummy‑Streams

## Installation (Backend)
1) Vom Repo‑Root aus in den Backend‑Ordner wechseln:
```bash
cd backend
```
2) Abhängigkeiten installieren (ohne virtuelle Umgebung):
```bash
pip3 install -r requirements.txt
```
Hinweis:
- Keine virtuelle Umgebung verwenden. Auf dem Raspberry Pi benötigt `picamera2` Systembibliotheken und läuft häufig nicht zuverlässig innerhalb eines venv.
- Wenn keine echte Kamera oder kein `picamera2` installiert ist, kann der Dummy‑Stream genutzt werden (siehe unten).

Hinweis: Auf dem Raspberry Pi können zusätzliche Systempakete für `picamera2` nötig sein. Prüfe ggf. offizielle Anleitungen (`libcamera`, `picamera2`). Für Tests ohne Kamera kann der Dummy‑Stream genutzt werden.

## Starten
- Direkt starten:
```bash
python3 backend/app.py
```
  - Der Server lauscht auf `0.0.0.0:5000`

- Alternativ mit Skript (vom Repo‑Root aus):
```bash
bash scripts/start_backend.sh
```

Falls auf dem Gerät keine echte Kamera verfügbar ist oder `picamera2` nicht installiert ist, setze eine der folgenden Optionen (Repo‑Root):
```bash
# Dummy-Stream erzwingen
USE_DUMMY_CAMERA=1 python3 backend/app.py

# oder echtes Kamera‑Erfordernis abschalten
REQUIRE_REAL_CAMERA=0 python3 backend/app.py
```

### Kamera‑Modi steuern
- Dummy erzwingen (keine echte Kamera notwendig):
```bash
export USE_DUMMY_CAMERA=1
python3 backend/app.py
```
- Echte Kamera erzwingen (Fehler, wenn nicht verfügbar):
```bash
export REQUIRE_REAL_CAMERA=1
python3 backend/app.py
```

## Nutzung
1) Browser öffnen und `http://<PI_IP>:5000/` aufrufen.
2) Rechtecke im Videobild ziehen, Kategorie wählen, an Backend senden.
3) Gespeicherte Zonen liegen in `backend/regions.json`.

## API
- `GET /video_feed`: MJPEG‑Stream
- `GET /regions`: Liefert gespeicherte Zonen
  - Antwort: `{ "regions": [ { x, y, width, height, category }, ... ], "videoResolution"?: { width, height } }`
- `POST /regions`: Speichert Zonen
  - Body JSON: `{ "regions": [ { x, y, width, height, category } ], "videoResolution"?: { width, height } }`
  - Wenn Werte normalisiert (≤1) sind und `videoResolution` gesetzt ist, werden sie in Pixel umgerechnet.
- `GET /healthz`: `{ "ok": true }`

## Entwicklung
- Frontend‑Assets liegen unter `frontend/static/`. Änderungen an `app.js`/`styles.css` werden beim Reload sichtbar.
- Logs: Das Flask‑Default‑Logging erscheint im Terminal. Eigene Logfiles (`backend.log`) können in `backend/` entstehen.

## Abhängigkeiten (kurz)
- Minimal benötigt: `Flask`, `flask-cors`, `Pillow`.
- Für echte Kamera: `picamera2` (in der Regel über Raspberry Pi OS/apt installierbar). Ohne `picamera2` läuft automatisch der Dummy‑Stream oder du setzt `USE_DUMMY_CAMERA=1`.

## Troubleshooting
- Kein Kamerabild: Setze `USE_DUMMY_CAMERA=1` zum Testen ohne Hardware.
- Port belegt: Passe den Port in `backend/app.py` an (`app.run(..., port=5000)`).
- Rechte/Abhängigkeiten auf dem Pi prüfen (`picamera2`, `libcamera`).

## Lizenz
MIT (falls nicht anders angegeben)

