# fusion_assistant_ReAct/retrieval/vectorstores.py
from __future__ import annotations
import os, json, csv
from typing import Dict, Iterable, List, Tuple

from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

from ..io.paths import DATASETS
from embeddings_oss import embeddings


# ---------- helpers ----------
def _iter_plain_texts(path: str) -> Iterable[Tuple[str, str]]:
    """
    Yield (relpath, text) for .txt/.md files.
    """
    for root, _, files in os.walk(path):
        for fn in files:
            if not fn.lower().endswith((".txt", ".md")):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    yield (os.path.relpath(fp, path), fh.read())
            except Exception:
                continue


def _iter_csv_rows(path: str) -> Iterable[Tuple[str, str]]:
    """
    For .csv files: each row becomes a small text blob.
    """
    for root, _, files in os.walk(path):
        for fn in files:
            if not fn.lower().endswith(".csv"):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    reader = csv.DictReader(fh)
                    for i, row in enumerate(reader):
                        yield (os.path.relpath(fp, path) + f":{i}", json.dumps(row, ensure_ascii=False))
            except Exception:
                continue


def _iter_json_docs(path: str) -> Iterable[Tuple[str, str]]:
    """
    - .json: whole file or top-level array elements
    - .jsonl: one item per line
    """
    for root, _, files in os.walk(path):
        for fn in files:
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, path)
            if fn.lower().endswith(".jsonl"):
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        for i, line in enumerate(fh):
                            line = line.strip()
                            if not line:
                                continue
                            yield (rel + f":{i}", line)
                except Exception:
                    continue
            elif fn.lower().endswith(".json"):
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        data = json.load(fh)
                    if isinstance(data, list):
                        for i, item in enumerate(data):
                            yield (rel + f":{i}", json.dumps(item, ensure_ascii=False))
                    else:
                        yield (rel, json.dumps(data, ensure_ascii=False))
                except Exception:
                    continue


def _load_documents(src_dir: str, *, source_name: str) -> List[Document]:
    texts: List[Tuple[str, str]] = []
    texts.extend(_iter_plain_texts(src_dir))
    texts.extend(_iter_csv_rows(src_dir))
    texts.extend(_iter_json_docs(src_dir))

    docs: List[Document] = []
    for relpath, text in texts:
        # ⬅️ Make filenames searchable by prefixing them into the content
        payload = f"TITLE: {relpath}\nDATASET: {source_name}\n\n{text or ''}"
        docs.append(
            Document(
                page_content=payload,
                metadata={
                    "path": relpath,
                    "dataset": source_name,
                },
            )
        )
    return docs


def _split_documents(docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    return splitter.split_documents(docs)


def _load_or_build_single(src: str, index_dir: str, source_name: str):
    """
    Return a FAISS vector store for one dataset. If index_dir exists, load it;
    otherwise build from source files.
    """
    os.makedirs(index_dir, exist_ok=True)
    faiss_idx = os.path.join(index_dir, "index.faiss")
    store_pkl = os.path.join(index_dir, "index.pkl")

    # Try load first
    if os.path.exists(faiss_idx) and os.path.exists(store_pkl):
        try:
            return FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)
        except Exception:
            # fall through to rebuild
            pass

    # Build
    if not os.path.isdir(src):
        # Empty store when no data dir exists—prevents hard crashes
        return FAISS.from_texts(["(empty dataset)"], embeddings)

    docs = _load_documents(src, source_name=source_name)
    if not docs:
        return FAISS.from_texts(["(no parsable files)"], embeddings)

    chunks = _split_documents(docs)
    vs = FAISS.from_documents(chunks, embeddings)
    vs.save_local(index_dir)
    return vs


# ---------- public API ----------
def build_or_load_all(datasets: Dict[str, Dict[str, str]] = DATASETS) -> Dict[str, FAISS]:
    """
    Build or load FAISS indices for every dataset in io.paths.DATASETS.
    Expected keys per entry: "src", "index", "source_name".
    Returns a map usable by build_retrievers_from_vectorstores().
    """
    vs_map: Dict[str, FAISS] = {}
    for key, cfg in datasets.items():
        src = cfg["src"]
        idx = cfg["index"]
        name = cfg.get("source_name", key)
        vs_map[key] = _load_or_build_single(src, idx, name)
    return vs_map
