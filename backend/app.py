import io
import json
import os
import threading
import time
from typing import Dict, List

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

from camera import Camera
from regions_store import RegionsStore


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))


def create_app() -> Flask:
    # Deaktiviere eingebaute Static-Route, damit wir unser Frontend aus /frontend bedienen
    app = Flask(__name__, static_folder=None)
    CORS(app)

    # Shared single camera instance
    camera = Camera()

    # Regions storage
    regions_store = RegionsStore(os.path.join(BASE_DIR, "regions.json"))

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/favicon.ico")
    def favicon():
        # Verhindert 404 im Browser-Log
        return ("", 204, {"Content-Type": "image/x-icon"})

    @app.route("/static/<path:path>")
    def static_files(path: str):
        return send_from_directory(os.path.join(FRONTEND_DIR, "static"), path)

    def mjpeg_generator():
        for frame in camera.frames():
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n"
                   b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n" +
                   frame + b"\r\n")

    @app.route("/video_feed")
    def video_feed():
        return Response(mjpeg_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/regions", methods=["GET", "POST", "OPTIONS"])
    def regions():
        if request.method == "OPTIONS":
            return ("", 204)

        if request.method == "GET":
            # Return pixel-based regions. Optionally include last known resolution.
            stored = regions_store.get_regions()
            # Try to infer resolution if stored as dict with meta
            resolution = None
            if stored and isinstance(stored, dict) and "regions" in stored:
                regions_list = stored.get("regions", [])
                resolution = stored.get("videoResolution")
            else:
                regions_list = stored if isinstance(stored, list) else []
            resp = {"regions": regions_list}
            if resolution:
                resp["videoResolution"] = resolution
            return jsonify(resp)

        # POST: accept pixel coordinates. If values appear normalized (<=1),
        # and videoResolution is provided, convert to pixels.
        try:
            payload = request.get_json(force=True, silent=False)
            regions_in = payload.get("regions", [])
            video_res = payload.get("videoResolution") or payload.get("resolution")
            vw = int(video_res.get("width")) if isinstance(video_res, dict) and video_res.get("width") is not None else None
            vh = int(video_res.get("height")) if isinstance(video_res, dict) and video_res.get("height") is not None else None

            pixel_regions: List[Dict] = []
            for r in regions_in:
                rx = float(r.get("x", 0))
                ry = float(r.get("y", 0))
                rw = float(r.get("width", 0))
                rh = float(r.get("height", 0))
                category = r.get("category") or "safe"
                if not isinstance(category, str):
                    category = str(category)
                category = category.strip()[:64] or "safe"

                # detect normalized input
                is_normalized = (rx <= 1.0 and ry <= 1.0 and rw <= 1.0 and rh <= 1.0 and vw and vh)
                if is_normalized:
                    x = int(round(rx * vw))
                    y = int(round(ry * vh))
                    w = int(round(rw * vw))
                    h = int(round(rh * vh))
                else:
                    x = int(round(rx))
                    y = int(round(ry))
                    w = int(round(rw))
                    h = int(round(rh))

                # clamp if resolution known
                if vw and vh:
                    x = max(0, min(vw, x))
                    y = max(0, min(vh, y))
                    w = max(0, min(vw, w))
                    h = max(0, min(vh, h))

                pixel_regions.append({
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "category": category,
                })

            # Store as plain list; also persist last resolution for reference
            to_store: Dict[str, object] = {"regions": pixel_regions}
            if vw and vh:
                to_store["videoResolution"] = {"width": vw, "height": vh}

            regions_store.set_regions(to_store)  # type: ignore[arg-type]
            return jsonify({"ok": True, "count": len(pixel_regions)})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.route("/healthz")
    def healthz():
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    app = create_app()
    # Bind to all interfaces for LAN access
    app.run(host="0.0.0.0", port=5000, threaded=True)


