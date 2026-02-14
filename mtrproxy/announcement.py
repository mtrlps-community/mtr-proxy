from typing import Dict, Optional, List
import requests

def fetch_announcement(api_url: str) -> Optional[Dict]:
    try:
        resp = requests.get(api_url, timeout=5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        return data
    except Exception:
        return None

def should_show_announcement(data: Dict, ignored_ids: List[str]) -> bool:
    ann_id = data.get("id")
    if not ann_id:
        return False
    # If force is true, always show
    if data.get("force", False):
        return True
    return ann_id not in ignored_ids
