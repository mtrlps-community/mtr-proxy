import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict


class ConfigManager:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = {}
        self._ensure_default()

    def _ensure_default(self) -> None:
        if not self._path.exists():
            self._data = {
                "client_id": str(uuid.uuid4()),
                "version": "1.0.0",
                "listen_host": "127.0.0.1",
                "listen_port": 1080,
                "auto_detect_enabled": False,
                "detect_interval_seconds": 60,
                "remote_nodes_api": "https://apimc.lnlfly.com/api/nodes",
                "announcement_api": "https://apimc.lnlfly.com/api/announcement",
                "heartbeat_api": "https://apimc.lnlfly.com/api/heartbeat",
                "update_api": "https://apimc.lnlfly.com/api/update",
                "ad_api": "https://apimc.lnlfly.com/api/ad",
                "ignored_announcement_ids": [],
                "ad": {
                    "type": "text",
                    "text": "欢迎使用mtr加速器",
                    "image_path": "",
                    "url": "https://your-sponsor-page.example"
                },
                "sponsor_links": [
                    {
                        "name": "lpsguide赞助",
                        "url": "https://www.lpsguide.cn/about/sponsorship/",
                        "image": ""
                    }
                ],
                "windows_autostart": False
            }
            self.save()
        else:
            self.reload()
            # Ensure client_id exists for old configs
            with self._lock:
                if "client_id" not in self._data:
                    self._data["client_id"] = str(uuid.uuid4())
                    self.save()
                if "version" not in self._data:
                    self._data["version"] = "1.0.0"
                    self.save()

    def reload(self) -> None:
        with self._lock:
            with self._path.open("r", encoding="utf-8") as f:
                self._data = json.load(f)

    def save(self) -> None:
        with self._lock:
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            self.save()

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def update_bulk(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self._data.update(data)
