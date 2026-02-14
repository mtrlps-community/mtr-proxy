import threading
import time
import requests
import socket
import platform
from typing import Dict, Any, Optional

class HeartbeatManager:
    def __init__(self, api_url: str, client_id: str, version: str, interval: int = 60):
        self.api_url = api_url
        self.client_id = client_id
        self.version = version
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._local_ip = self._get_local_ip()
        self._os_name = platform.system().lower()

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Doesn't need to be reachable
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self, extra_data: Dict[str, Any] = None):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, 
            args=(extra_data or {},), 
            daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self, extra_data: Dict[str, Any]):
        while not self._stop_event.is_set():
            try:
                payload = {
                    "client_id": self.client_id,
                    "version": self.version,
                    "ip": self._local_ip,
                    "os": self._os_name,
                    "timestamp": int(time.time()),
                    **extra_data
                }
                headers = {
                    "X-Client-ID": self.client_id,
                    "X-Client-Version": self.version
                }
                requests.post(self.api_url, json=payload, headers=headers, timeout=5)
            except Exception:
                pass # Ignore heartbeat errors
            
            for _ in range(self.interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1)
