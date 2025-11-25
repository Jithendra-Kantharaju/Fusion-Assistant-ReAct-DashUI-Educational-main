"""
Utilities for reading raw files from a directory into LangChain Documents,
and batching them by token count for FAISS ingestion.
"""

from __future__ import annotations
import os
from typing import List, Iterable, Optional
from langchain.schema import Document
from ..util.token import count_tokens


def _read_text(path: str, encoding: str = "utf-8") -> str:
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        return f.read()


def _read_csv_skip_header(path: str, encoding: str = "utf-8") -> str:
    # Preserve line breaks; skip header row (common for your datasets)
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        lines = f.readlines()
    return "".join(lines[1:]) if len(lines) > 1 else ""


def _read_jsonl_verbatim(path: str, encoding: str = "utf-8") -> str:
    # Keep as raw lines so chunks stay human-readable in retrieval
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        return f.read()


def load_text_files_from_directory(
    directory_path: str,
    source_name: str,
    *,
    extensions: Optional[Iterable[str]] = (".txt", ".csv", ".jsonl"),
    encoding: str = "utf-8",
) -> List[Document]:
    """
    Walk a directory recursively and convert supported files to Documents.

    - .txt  → full file
    - .csv  → all rows except header (keeps newlines)
    - .jsonl→ raw lines verbatim (no parsing)

    metadata: {"source": f"{source_name}_<YYYY_MM_DD?>", "filename": <name>, "path": <abs>}
    """
    documents: List[Document] = []
    if not directory_path or not os.path.isdir(directory_path):
        return documents

    exts = tuple(extensions or ())

    for root, _, files in os.walk(directory_path):
        for filename in files:
            if exts and not filename.lower().endswith(exts):
                continue

            fpath = os.path.join(root, filename)

            try:
                if filename.lower().endswith(".txt"):
                    content = _read_text(fpath, encoding)
                elif filename.lower().endswith(".csv"):
                    content = _read_csv_skip_header(fpath, encoding)
                elif filename.lower().endswith(".jsonl"):
                    content = _read_jsonl_verbatim(fpath, encoding)
                else:
                    continue
            except Exception:
                # Skip unreadable files but keep walking
                continue

            documents.append(
                Document(
                    page_content=content or "",
                    metadata={
                        "source": source_name,
                        "filename": filename,
                        "path": os.path.abspath(fpath),
                    },
                )
            )

    return documents


def batch_documents(
    documents: List[Document],
    *,
    max_tokens: int = 250_000,
    model_used: str = "text-embedding-3-large",
) -> List[List[Document]]:
    """
    Split a list of Documents into batches whose total token count per batch
    does not exceed `max_tokens`.

    Raises:
        ValueError if any single document exceeds `max_tokens`.
    """
    batches: List[List[Document]] = []
    current_batch: List[Document] = []
    current_tokens = 0

    for doc in documents:
        tokens = count_tokens(doc.page_content, model_used=model_used)
        if tokens > max_tokens:
            raise ValueError(f"Single document too large: {tokens} tokens — {doc.metadata.get('filename')}")

        if current_tokens + tokens > max_tokens:
            if current_batch:
                batches.append(current_batch)
            current_batch = [doc]
            current_tokens = tokens
        else:
            current_batch.append(doc)
            current_tokens += tokens

    if current_batch:
        batches.append(current_batch)

    return batches
