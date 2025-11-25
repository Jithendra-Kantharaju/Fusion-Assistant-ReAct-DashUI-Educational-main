"""
Small general-purpose helpers used across the backend.
Keep this file dependency-light so it can be imported anywhere.
"""

from __future__ import annotations
from typing import Iterable, Iterator, List, Sequence, Tuple, TypeVar
from datetime import datetime

T = TypeVar("T")


def now_utc_iso() -> str:
    """Current UTC time in ISO 8601 (Z) format, second precision."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def batched(seq: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yield chunks of length `size` (last chunk may be smaller)."""
    if size <= 0:
        raise ValueError("size must be > 0")
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def dedupe_preserve_order(items: Iterable[T]) -> List[T]:
    """Remove duplicates while preserving first-seen order (case-sensitive)."""
    seen = set()
    out: List[T] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def chunk_text(text: str, max_chars: int = 10_000) -> List[str]:
    """
    Split text on paragraph boundaries without exceeding max_chars per chunk.
    Falls back to hard slicing if paragraphs are very long.
    """
    if not text:
        return [""]
    paras = (text or "").split("\n")
    chunks: List[str] = []
    cur = ""
    for p in paras:
        # +1 for the newline we add back
        if len(cur) + len(p) + 1 <= max_chars:
            cur += p + "\n"
        else:
            if cur.strip():
                chunks.append(cur.strip())
            # very long single paragraph: slice hard
            if len(p) > max_chars:
                for i in range(0, len(p), max_chars):
                    chunks.append(p[i : i + max_chars])
                cur = ""
            else:
                cur = p + "\n"
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def normalize_chain_result(result) -> str:
    """
    Convert a variety of chain return types into a displayable string.
    Looks for common keys before stringifying the whole object.
    """
    if isinstance(result, dict):
        for k in ("answer", "result", "output", "content", "text"):
            v = result.get(k)
            if isinstance(v, str) and v.strip():
                return v
        # fallback to compact string
        try:
            import json
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return str(result)
    return str(result)
