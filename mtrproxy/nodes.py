import threading
import time
from typing import Callable, Dict, List, Optional
import requests
import socket
from .types import NodeInfo

class NodeManager:
    def __init__(
        self,
        remote_api: str,
        detect_interval_seconds: int,
        auto_detect_enabled: bool,
        on_nodes_updated: Optional[Callable[[List[NodeInfo]], None]] = None,
        on_best_node_changed: Optional[Callable[[Optional[NodeInfo]], None]] = None,
    ):
        self.remote_api = remote_api
        self.detect_interval_seconds = detect_interval_seconds
        self.auto_detect_enabled = auto_detect_enabled
        self.on_nodes_updated = on_nodes_updated
        self.on_best_node_changed = on_best_node_changed

        self._nodes: Dict[str, NodeInfo] = {}
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._current_node_key: Optional[str] = None
        self._manual_selected = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            # No auto detect loop anymore
            for _ in range(self.detect_interval_seconds):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def fetch_nodes_from_remote(self) -> List[NodeInfo]:
        try:
            resp = requests.get(self.remote_api, timeout=5)
            resp.raise_for_status()
            arr = resp.json()
            nodes: List[NodeInfo] = []
            for item in arr:
                enabled = item.get("enabled", True)
                if not enabled:
                    continue
                nodes.append(
                    NodeInfo(
                        hostname=item.get("hostname") or item.get("name", ""),
                        ip=item["ip"],
                        port=int(item["port"]),
                        enabled=enabled,
                        group=item.get("group", "默认"),
                        priority=item.get("priority", 100),
                        motd=item.get("motd"),
                        online_count=item.get("online_count", 0),
                    )
                )
            with self._lock:
                # Update existing nodes but preserve latency if possible, or just overwrite
                # If we overwrite, we lose current latency until next ping. Let's just overwrite for simplicity or merge.
                # Merging is better to keep latency info if IP/port hasn't changed.
                new_nodes = {}
                for n in nodes:
                    if n.hostname in self._nodes:
                        old = self._nodes[n.hostname]
                        if old.ip == n.ip and old.port == n.port:
                            n.latency_ms = old.latency_ms
                            n.reachable = old.reachable
                            n.status = old.status
                    new_nodes[n.hostname] = n
                self._nodes = new_nodes
            
            self._notify_nodes_updated()
            return nodes
        except Exception as e:
            # In a real app, log this
            print(f"Error fetching nodes: {e}")
            return []

    def _notify_nodes_updated(self) -> None:
        if self.on_nodes_updated:
            with self._lock:
                nodes = list(self._nodes.values())
            self.on_nodes_updated(nodes)

    def list_nodes(self) -> List[NodeInfo]:
        with self._lock:
            return list(self._nodes.values())

    def get_current_node(self) -> Optional[NodeInfo]:
        with self._lock:
            if not self._current_node_key:
                return None
            return self._nodes.get(self._current_node_key)

    def manual_select_node(self, hostname: str) -> Optional[NodeInfo]:
        with self._lock:
            node = self._nodes.get(hostname)
            if node:
                self._current_node_key = hostname
                self._manual_selected = True
        if self.on_best_node_changed:
            self.on_best_node_changed(self.get_current_node())
        return self.get_current_node()

    def clear_manual_select(self) -> None:
        with self._lock:
            self._manual_selected = False

    def detect_latency(self, node: NodeInfo, timeout: float = 2.0) -> NodeInfo:
        start = time.time()
        reachable = False
        try:
            # MC Ping Logic
            s = socket.create_connection((node.ip, node.port), timeout=timeout)
            
            def pack_varint(d):
                o = b''
                while True:
                    b = d & 0x7F
                    d >>= 7
                    o += bytes([b | (0x80 if d > 0 else 0)])
                    if d == 0: break
                return o

            def pack_string(text):
                d = text.encode('utf8')
                return pack_varint(len(d)) + d

            # 1. Handshake
            # Packet ID 0x00, Protocol 47 (1.8), Host, Port, NextState 1 (Status)
            handshake_payload = (
                b'\x00' + 
                pack_varint(47) + 
                pack_string(node.ip) + 
                int(node.port).to_bytes(2, 'big') + 
                pack_varint(1)
            )
            s.send(pack_varint(len(handshake_payload)) + handshake_payload)

            # 2. Request Status
            # Packet ID 0x00
            request_payload = b'\x00'
            s.send(pack_varint(len(request_payload)) + request_payload)

            # 3. Wait for response
            # Read response length (VarInt) - first byte implies data arrived
            s.recv(1) 
            
            s.close()
            reachable = True
        except Exception:
            reachable = False
        
        end = time.time()
        latency = (end - start) * 1000 if reachable else None
        node.latency_ms = latency
        node.reachable = reachable
        if not reachable:
            node.status = "unreachable"
        elif latency is not None and latency < 50:
            node.status = "good"
        elif latency is not None and latency < 150:
            node.status = "normal"
        else:
            node.status = "slow"
        return node

    def detect_all_nodes(self, auto_switch: bool) -> None:
        with self._lock:
            nodes = list(self._nodes.values())
        
        # Parallel detection could be faster, but let's stick to simple sequential or threaded
        # The original code used threads for pinging. Let's do that.
        threads = []
        for n in nodes:
            t = threading.Thread(target=self.detect_latency, args=(n,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        best: Optional[NodeInfo] = None
        for n in nodes:
            if n.reachable and n.latency_ms is not None:
                if not best or n.latency_ms < best.latency_ms:
                    best = n
        
        with self._lock:
            # Nodes are objects, so they are updated in place, but we need to ensure the dict is current
            pass
            
        if auto_switch and best:
            with self._lock:
                self._current_node_key = best.hostname
            if self.on_best_node_changed:
                self.on_best_node_changed(best)
        
        self._notify_nodes_updated()
