import json
import os
import threading
from typing import List, Dict


class RegionsStore:
    def __init__(self, json_path: str) -> None:
        self.json_path = json_path
        self._lock = threading.Lock()
        self._regions = []  # type: ignore[var-annotated]
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.json_path):
            self._regions = []
            return
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # allow either list or dict with regions+videoResolution
            if isinstance(data, dict):
                if "regions" in data:
                    self._regions = data
                else:
                    # legacy: consider whole dict as regions list fallback
                    self._regions = {"regions": list(data)}
            elif isinstance(data, list):
                self._regions = {"regions": list(data)}
        except Exception:
            self._regions = []

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        tmp_path = f"{self.json_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            if isinstance(self._regions, dict):
                json.dump(self._regions, f, ensure_ascii=False, indent=2)
            else:
                json.dump({"regions": self._regions}, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.json_path)

    def get_regions(self):  # returns list or dict with metadata
        with self._lock:
            return json.loads(json.dumps(self._regions))

    def set_regions(self, regions_or_dict) -> None:
        with self._lock:
            self._regions = regions_or_dict
            self._save()


