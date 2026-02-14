import requests
from typing import Dict, Optional, Tuple

def check_update(api_url: str, current_version: str) -> Tuple[bool, Optional[Dict]]:
    try:
        resp = requests.get(api_url, timeout=5)
        if resp.status_code != 200:
            return False, None
        
        data = resp.json()
        latest = data.get("latest_version")
        if not latest:
            return False, None
            
        # Simple string comparison or semantic versioning?
        # User said: latest_version > current_version -> popup
        # We can use packaging.version if available, or simple split.
        # Let's assume simple string compare for now or basic semantic check.
        if _is_newer(latest, current_version):
            return True, data
            
        return False, None
    except Exception:
        return False, None

def _is_newer(latest: str, current: str) -> bool:
    # Basic semantic version compare
    try:
        l_parts = [int(x) for x in latest.split('.')]
        c_parts = [int(x) for x in current.split('.')]
        
        # Pad with zeros
        while len(l_parts) < len(c_parts): l_parts.append(0)
        while len(c_parts) < len(l_parts): c_parts.append(0)
        
        return l_parts > c_parts
    except ValueError:
        return latest > current # Fallback string compare
