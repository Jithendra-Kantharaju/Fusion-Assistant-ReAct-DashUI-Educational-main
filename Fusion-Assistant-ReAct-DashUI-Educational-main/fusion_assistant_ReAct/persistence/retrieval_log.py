# fusion_assistant_ReAct/persistence/retrieval_log.py
from __future__ import annotations
import json, os, io, threading
from datetime import datetime
from typing import Any, Dict

_lock = threading.Lock()

def _ts() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def append_jsonl(record: Dict[str, Any], path: str) -> None:
    """
    Append a single JSON object as a line to `path`.
    Creates the directory if needed. Thread-safe.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with _lock:
        with io.open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
