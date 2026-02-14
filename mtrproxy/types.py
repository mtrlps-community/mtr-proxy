from dataclasses import dataclass
from typing import Optional


@dataclass
class NodeInfo:
    hostname: str
    ip: str
    port: int
    enabled: bool = True
    group: str = "默认"
    priority: int = 100
    motd: Optional[str] = None
    online_count: int = 0
    latency_ms: Optional[float] = None
    reachable: bool = False
    status: str = "unknown"


@dataclass
class ProxyStatus:
    running: bool
    current_node: Optional[NodeInfo]
    listen_port: int
    uptime_seconds: int
    active_connections: int
    current_latency_ms: Optional[float]
