import json, os, tempfile, time, errno
from contextlib import contextmanager
from datetime import datetime
from typing import Any, List
from langchain.schema import Document

def documents_to_json_serializable(documents: List[Document]):
    out = []
    for doc in documents:
        out.append({"metadata": doc.metadata, "content": doc.page_content})
    return out

@contextmanager
def _file_lock(lock_path, timeout=5.0):
    start = time.time()
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd); break
        except OSError as e:
            if e.errno != errno.EEXIST: raise
            if time.time() - start > timeout: break
            time.sleep(0.05)
    try:
        yield
    finally:
        try: os.remove(lock_path)
        except FileNotFoundError: pass

def _safe_load_json_array(path: str):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[store_chatHist] Warning: could not read {path}: {e}. Resetting to [].")
        return []

def _atomic_write_json(path: str, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    dir_ = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=dir_, delete=False) as tmp:
        json.dump(obj, tmp, indent=4, ensure_ascii=False)
        tmp.flush(); os.fsync(tmp.fileno()); tmp_path = tmp.name
    os.replace(tmp_path, path)

def _normalize_response(resp: Any) -> str:
    if isinstance(resp, dict):
        for k in ("answer","result","output","content","text"):
            v = resp.get(k)
            if isinstance(v, str) and v.strip():
                return v
        return json.dumps(resp, ensure_ascii=False)
    return str(resp)

def store_chatHist(question, response, context, json_file_path):
    response = _normalize_response(response)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lock_path = f"{json_file_path}.lock"
    with _file_lock(lock_path):
        chat_data = _safe_load_json_array(json_file_path)
        for entry in chat_data:
            if entry.get("question") == question and entry.get("response") == response:
                print(f"[store_chatHist] Duplicate skipped for {json_file_path}.")
                return
        chat_data.append({"question": question, "context": context, "response": response, "timestamp": timestamp})
        _atomic_write_json(json_file_path, chat_data)
        print(f"[store_chatHist] Appended to {json_file_path}.")
