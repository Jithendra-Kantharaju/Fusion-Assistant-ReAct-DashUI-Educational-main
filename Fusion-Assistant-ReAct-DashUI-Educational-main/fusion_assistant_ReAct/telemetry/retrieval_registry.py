# fusion_assistant_ReAct/telemetry/retrieval_registry.py
from __future__ import annotations
from collections import deque
from typing import Deque, Dict, Any, List

# Simple in-memory ring buffer to show recent retrievals in the UI
_REGISTRY: Deque[Dict[str, Any]] = deque(maxlen=200)

def push(record: Dict[str, Any]) -> None:
    _REGISTRY.appendleft(record)

def get_recent(limit: int = 20) -> List[Dict[str, Any]]:
    return list(list(_REGISTRY)[:limit])
