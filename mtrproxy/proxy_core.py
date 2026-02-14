import socket
import threading
import time
from typing import Callable, Optional

from .nodes import NodeManager
from .types import ProxyStatus, NodeInfo


class ProxyServer:
    def __init__(
        self,
        listen_host: str,
        listen_port: int,
        node_manager: NodeManager,
        on_status: Optional[Callable[[ProxyStatus], None]] = None,
    ):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.node_manager = node_manager
        self.on_status = on_status

        self._server_sock: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._active_connections = 0
        self._start_time: Optional[float] = None

    def start(self) -> None:
        with self._lock:
            if self._server_sock:
                return
            try:
                self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._server_sock.bind((self.listen_host, self.listen_port))
                self._server_sock.listen(128)
                self._stop_event.clear()
                self._start_time = time.time()
                self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
                self._accept_thread.start()
            except Exception as e:
                print(f"Failed to start proxy: {e}")
                if self._server_sock:
                    self._server_sock.close()
                self._server_sock = None
        self._notify_status()

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            if self._server_sock:
                try:
                    self._server_sock.close()
                except OSError:
                    pass
                self._server_sock = None
        if self._accept_thread:
            self._accept_thread.join(timeout=2)
        self._notify_status()

    def _accept_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if not self._server_sock:
                    break
                client_sock, addr = self._server_sock.accept()
            except OSError:
                break
            except Exception:
                continue
            
            threading.Thread(
                target=self._handle_client, args=(client_sock, addr), daemon=True
            ).start()

    def _handle_client(self, client_sock: socket.socket, addr) -> None:
        with self._lock:
            self._active_connections += 1
        self._notify_status()
        backend_sock: Optional[socket.socket] = None
        try:
            node = self.node_manager.get_current_node()
            if not node or not node.reachable:
                # Try to detect if it's reachable just in case it wasn't checked recently?
                # For now, just close if marked unreachable or None
                client_sock.close()
                return
            
            # Connect to backend
            backend_sock = socket.create_connection((node.ip, node.port), timeout=5)
            self._relay(client_sock, backend_sock)
        except Exception:
            pass
        finally:
            try:
                client_sock.close()
            except OSError:
                pass
            if backend_sock:
                try:
                    backend_sock.close()
                except OSError:
                    pass
            with self._lock:
                self._active_connections -= 1
            self._notify_status()

    def _relay(self, c: socket.socket, s: socket.socket) -> None:
        def forward(src: socket.socket, dst: socket.socket) -> None:
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except OSError:
                pass
            finally:
                try:
                    dst.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

        t1 = threading.Thread(target=forward, args=(c, s), daemon=True)
        t2 = threading.Thread(target=forward, args=(s, c), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def _notify_status(self) -> None:
        if not self.on_status:
            return
        with self._lock:
            running = self._server_sock is not None
            active = self._active_connections
            uptime = 0
            if self._start_time and running:
                uptime = int(time.time() - self._start_time)
        
        node: Optional[NodeInfo] = self.node_manager.get_current_node()
        latency = node.latency_ms if node else None
        
        status = ProxyStatus(
            running=running,
            current_node=node,
            listen_port=self.listen_port,
            uptime_seconds=uptime,
            active_connections=active,
            current_latency_ms=latency,
        )
        self.on_status(status)
