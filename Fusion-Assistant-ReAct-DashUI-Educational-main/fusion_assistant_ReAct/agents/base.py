from typing import Any, Dict

def normalize_chain_result(res: Any) -> str:
    if isinstance(res, dict):
        for k in ("answer","result","output","content","text"):
            v = res.get(k)
            if isinstance(v, str) and v.strip():
                return v
        return str(res)
    return str(res)
