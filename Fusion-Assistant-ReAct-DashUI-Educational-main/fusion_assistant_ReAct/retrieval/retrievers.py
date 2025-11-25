"""
Retriever utilities with:
- Labeled sub-retrievers (e.g., "lcel", "query")
- Cross-retriever de-duplication (content-hash based, prefers 'query')
- Balanced merging so 'query' examples appear for LQEL-style queries
- JSONL logging with per-source breakdown
- UI registry feed for the Dash panel
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, DefaultDict
from collections import defaultdict, deque
from hashlib import sha1
from datetime import datetime

from pydantic import Field
from langchain.schema import Document, BaseRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun

from ..persistence.retrieval_log import append_jsonl
from ..io.paths import RETRIEVAL_LOG
from ..telemetry import retrieval_registry as _registry


def _ts() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


_LQEL_TOKENS = (
    "lqel", "lcel", "where(", "groupby(", "calculate(", "icontains", "istarts-with", "nocase("
)


def _content_hash(doc: Document) -> str:
    return sha1((doc.page_content or "")[:2000].encode("utf-8", errors="ignore")).hexdigest()


class CombinedRetriever(BaseRetriever):
    """
    Concatenates results from multiple retrievers, adds an origin label, dedupes,
    and balances output so the 'query' store contributes when appropriate.
    """
    retrievers: List[BaseRetriever] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)   # same length/order as retrievers
    limit: int = Field(default=5)
    log_path: Optional[str] = Field(default=RETRIEVAL_LOG)

    def _invoke_all(self, query: str, *, async_mode: bool = False) -> List[Document]:
        if self.labels and len(self.labels) != len(self.retrievers):
            self.labels = [f"r{i}" for i in range(len(self.retrievers))]

        # Invoke retrievers
        docs_all: List[Document] = []
        if not async_mode:
            for lbl, r in zip(self.labels or [], self.retrievers):
                results = r.invoke(query)
                for d in results:
                    md = dict(d.metadata or {})
                    md["_retriever"] = lbl
                    d.metadata = md
                docs_all.extend(results)
        else:
            import asyncio
            async def _g():
                batches = await asyncio.gather(*(r.ainvoke(query) for r in self.retrievers), return_exceptions=True)
                out: List[Document] = []
                for lbl, res in zip(self.labels or [], batches):
                    docs = [] if isinstance(res, Exception) else res
                    for d in docs:
                        md = dict(d.metadata or {})
                        md["_retriever"] = lbl
                        d.metadata = md
                    out.extend(docs)
                return out
            docs_all = asyncio.get_event_loop().run_until_complete(_g())

        # De-dupe by content hash; prefer 'query' when duplicate text appears
        chosen: Dict[str, Document] = {}
        for d in docs_all:
            h = _content_hash(d)
            cur = chosen.get(h)
            if cur is None:
                chosen[h] = d
                continue
            # prefer 'query' origin over others if same content
            prev_src = (cur.metadata or {}).get("_retriever", "")
            new_src  = (d.metadata or {}).get("_retriever", "")
            if prev_src != "query" and new_src == "query":
                chosen[h] = d

        deduped = list(chosen.values())
        return deduped

    def _balanced_slice(self, query: str, docs: List[Document]) -> List[Document]:
        """
        Ensure the 'query' store gets visibility for LQEL-style queries.
        Strategy:
          1) Bucket by origin label
          2) If query contains LQEL tokens and 'query' exists, take up to 2 from 'query' first
          3) Fill the rest round-robin across sources
        """
        by_src: DefaultDict[str, deque] = defaultdict(deque)
        for d in docs:
            by_src[(d.metadata or {}).get("_retriever", "")].append(d)

        out: List[Document] = []
        want_query_boost = any(t in query.lower() for t in _LQEL_TOKENS)
        if want_query_boost and "query" in by_src:
            for _ in range(2):
                if by_src["query"]:
                    out.append(by_src["query"].popleft())
                if len(out) >= self.limit:
                    return out[: self.limit]

        # round-robin fill
        sources = list(by_src.keys())
        i = 0
        while len(out) < self.limit and any(by_src.values()):
            src = sources[i % len(sources)]
            if by_src[src]:
                out.append(by_src[src].popleft())
            i += 1

        return out[: self.limit]

    def _log(self, query: str, docs: List[Document]) -> None:
        try:
            by_src_counts: Dict[str, int] = {}
            payload_docs = []
            for d in docs:
                md = dict(d.metadata or {})
                src = md.get("_retriever", "")
                by_src_counts[src] = by_src_counts.get(src, 0) + 1
                payload_docs.append(
                    {
                        "content_preview": (d.page_content or "")[:500],
                        "metadata": md,
                    }
                )
            rec = {
                "ts": _ts(),
                "query": query,
                "result_count": len(docs),
                "by_source": by_src_counts,
                "docs": payload_docs,
            }
            if self.log_path:
                append_jsonl(rec, self.log_path)
            _registry.push(rec)
        except Exception:
            pass

    # ---- BaseRetriever hooks ----
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        all_docs = self._invoke_all(query, async_mode=False)
        final_docs = self._balanced_slice(query, all_docs)
        try:
            run_manager.on_retriever_end(final_docs)
        except Exception:
            pass
        self._log(query, final_docs)
        return final_docs

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        all_docs = self._invoke_all(query, async_mode=True)
        final_docs = self._balanced_slice(query, all_docs)
        try:
            await run_manager.on_retriever_end(final_docs)
        except Exception:
            pass
        self._log(query, final_docs)
        return final_docs

    def with_config(self, **kwargs):
        return self


def mmr(vs, *, k: int = 10, lambda_mult: float = 0.7, fetch_k: int | None = None):
    kwargs = {"k": k, "lambda_mult": lambda_mult}
    if fetch_k is not None:
        kwargs["fetch_k"] = fetch_k
    return vs.as_retriever(search_type="mmr", search_kwargs=kwargs)


def build_retrievers_from_vectorstores(vs_map: Dict[str, any]) -> Dict[str, BaseRetriever | CombinedRetriever | dict]:
    """
    Build labeled, balanced retrievers for the app.
    Expected vs_map keys:
      scenario1, sigma, cve, cwe, capec, ics, lcel, asset, query
    """
    # Raw MMR retrievers
    r_sigma    = mmr(vs_map["sigma"])
    r_scenario = mmr(vs_map["scenario1"])
    r_cve      = mmr(vs_map["cve"])
    r_cwe      = mmr(vs_map["cwe"])
    r_capec    = mmr(vs_map["capec"])
    r_ics      = mmr(vs_map["ics"])
    r_lcel     = mmr(vs_map["lcel"], k=4, fetch_k=20, lambda_mult=0.7)  # smaller, more focused
    r_asset    = mmr(vs_map["asset"], k=4, fetch_k=20, lambda_mult=0.7) # smaller, more focused
    r_query    = mmr(vs_map["query"], k=4, fetch_k=20, lambda_mult=0.7)  # broader for example snippets

    # Combined domains (labels align to order)
    code_combined  = CombinedRetriever(retrievers=[r_cve, r_cwe], labels=["cve", "cwe"], limit=2)
    log_combined   = CombinedRetriever(retrievers=[r_scenario], labels=["scenario1"], limit=2)
    lcel_combined  = CombinedRetriever(retrievers=[r_lcel, r_query], labels=["lcel", "query"], limit=2)
    asset_combined = CombinedRetriever(retrievers=[r_asset], labels=["asset"], limit=2)

    return {
        "code": code_combined,
        "log": log_combined,
        "lcel": lcel_combined,
        "asset": asset_combined,
        "_raw": {
            "sigma": r_sigma,
            "capec": r_capec,
            "ics": r_ics,
            "scenario1": r_scenario,
            "cve": r_cve,
            "cwe": r_cwe,
            "lcel": r_lcel,
            "asset": r_asset,
            "query": r_query,
        },
    }
