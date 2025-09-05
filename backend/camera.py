import io
import os
import time
import threading
from typing import Generator

from PIL import Image, ImageDraw

try:
    from picamera2 import Picamera2
except Exception:  # pragma: no cover
    Picamera2 = None  # type: ignore


class _BaseCamera:
    def frames(self) -> Generator[bytes, None, None]:  # pragma: no cover - abstract
        raise NotImplementedError


class _PiCamera(_BaseCamera):
    def __init__(self, width: int, height: int, fps: int) -> None:
        if Picamera2 is None:
            raise RuntimeError("picamera2 nicht verfügbar")
        self.width = width
        self.height = height
        self.fps = fps
        self._frame_lock = threading.Lock()
        self._last_frame: bytes | None = None
        self._running = True
        self.picam = Picamera2()
        config = self.picam.create_video_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        self.picam.configure(config)
        self.picam.start()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def _capture_loop(self) -> None:
        target_interval = 1.0 / float(self.fps)
        while self._running:
            start = time.time()
            frame_array = self.picam.capture_array()
            image = Image.fromarray(frame_array)
            buf = io.BytesIO()
            image.save(buf, format="JPEG", quality=85)
            jpeg_bytes = buf.getvalue()
            with self._frame_lock:
                self._last_frame = jpeg_bytes
            elapsed = time.time() - start
            sleep_for = max(0.0, target_interval - elapsed)
            if sleep_for:
                time.sleep(sleep_for)

    def frames(self) -> Generator[bytes, None, None]:
        while True:
            with self._frame_lock:
                data = self._last_frame
            if data is not None:
                yield data
            time.sleep(1.0 / 30.0)


class _DummyCamera(_BaseCamera):
    def __init__(self, width: int, height: int, fps: int) -> None:
        self.width = width
        self.height = height
        self.fps = fps

    def frames(self) -> Generator[bytes, None, None]:
        t = 0
        while True:
            img = Image.new("RGB", (self.width, self.height), (20, 20, 20))
            draw = ImageDraw.Draw(img)
            # moving rectangle
            x = (t % self.width)
            draw.rectangle([(x, 40), (min(self.width-1, x+100), 140)], outline=(0,255,136), width=4)
            # grid
            for gx in range(0, self.width, 40):
                draw.line([(gx,0),(gx,self.height)], fill=(60,60,60))
            for gy in range(0, self.height, 40):
                draw.line([(0,gy),(self.width,gy)], fill=(60,60,60))
            # text
            msg = "Dummy-Stream (keine Kamera erkannt)"
            draw.text((12, self.height-28), msg, fill=(255,255,255))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            yield buf.getvalue()
            t += 8
            time.sleep(1.0/float(self.fps))


class Camera(_BaseCamera):
    """Camera wrapper. Fällt automatisch auf Dummy zurück, wenn Pi-Kamera nicht verfügbar ist."""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 15) -> None:
        use_dummy = os.environ.get("USE_DUMMY_CAMERA", "0") == "1"
        require_real = os.environ.get("REQUIRE_REAL_CAMERA", "0") == "1"
        self.impl: _BaseCamera
        if not use_dummy:
            try:
                self.impl = _PiCamera(width, height, fps)
                return
            except Exception:
                if require_real:
                    # Hard-Fail ohne Fallback, wenn explizit echte Kamera gefordert ist
                    raise
                # sonst Fallback auf Dummy erlauben
                self.impl = _DummyCamera(width, height, fps)
                return
        # explizit Dummy
        self.impl = _DummyCamera(width, height, fps)

    def frames(self) -> Generator[bytes, None, None]:
        return self.impl.frames()


