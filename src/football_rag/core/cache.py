"""
Simple in-memory TTL cache.
Why: reduce repeated LLM work; safe and local for a POC.
"""

import time
from typing import Any, Dict, Optional, Tuple

_Entry = Tuple[Any, float]  # (value, expires_at)


class SimpleCache:
    def __init__(self) -> None:
        self._data: Dict[str, _Entry] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._data.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if expires_at and time.time() > expires_at:
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds > 0 else 0.0
        self._data[key] = (value, expires_at)


cache = SimpleCache()
