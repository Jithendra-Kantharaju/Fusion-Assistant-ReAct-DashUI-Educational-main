# fusion_assistant_ReAct/agents/lcel_agent.py
from __future__ import annotations
from typing import Any, Optional
import os, re, json

from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from ..llm.models import get_default_doc_llm

try:
    from prompts import LCEL_Query_Prompt as DEFAULT_LCEL_TEMPLATE
except Exception:
    DEFAULT_LCEL_TEMPLATE = (
        "You are an LQEL (Log Query Expression Language) assistant.\n"
        "Conversation history:\n{history}\n\n"
        "Task/context:\n{context}\n\n"
        "Return an LQEL expression or a concise, executable query plan."
    )

# ----------------------------- utilities -----------------------------

def as_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if hasattr(x, "content"):
        try:
            c = getattr(x, "content")
            if isinstance(c, str):
                return c
        except Exception:
            pass
    if isinstance(x, dict):
        for k in ("answer", "result", "output_text", "content", "text"):
            v = x.get(k)
            if isinstance(v, str):
                return v
        try:
            return json.dumps(x, indent=2, ensure_ascii=False)
        except Exception:
            return str(x)
    if hasattr(x, "model_dump_json"):
        try:
            return x.model_dump_json(indent=2)
        except Exception:
            pass
    return str(x)

_LQEL_TOKENS = ("where(", "groupby(", "calculate(", "istarts-with", "icontains", "nocase(")

def _looks_like_lqel(text: str) -> bool:
    t = text.lower()
    if "```lqel" in t:
        return True
    return any(tok in t for tok in _LQEL_TOKENS)

_SQL_SIGNS = re.compile(
    r"```sql|^\s*select\b|^\s*with\b|^\s*insert\b|^\s*update\b|^\s*delete\b| from\b| join\b",
    flags=re.IGNORECASE | re.MULTILINE,
)

def _looks_like_sql(text: str) -> bool:
    return bool(_SQL_SIGNS.search(text or ""))

def _extract_lqel_block(text: str) -> Optional[str]:
    if not text:
        return None
    m = re.search(r"```lqel\s*(.+?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        body = m.group(1).strip()
        return body if _looks_like_lqel(body) else None
    for mm in re.finditer(r"```([a-zA-Z0-9_]*)\s*(.+?)```", text, flags=re.DOTALL):
        body = mm.group(2).strip()
        if _looks_like_lqel(body):
            return body
    if _looks_like_lqel(text):
        idxs = [text.lower().find(tok) for tok in _LQEL_TOKENS if tok in text.lower()]
        idx = min(idxs) if idxs else -1
        if idx >= 0:
            snippet = text[idx:]
            snippet = re.split(r"\n\s*\n", snippet, maxsplit=1)[0].strip()
            return snippet
    return None

def _wrap_as_lqel(body: str) -> str:
    body = (body or "").strip()
    return f"```lqel\n{body}\n```" if body else "```lqel\n```"

# ------------------------ LCEL repair scaffolding ---------------------

def _build_repair_chain(llm):
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You convert queries into the Log Query Expression Language (LQEL).\n"
                    "Rules (MANDATORY):\n"
                    "1) Output ONLY one code block fenced as ```lqel ...``` with the final LQEL.\n"
                    "2) NEVER use SQL or SQL-like syntax (no SELECT, FROM, JOIN, CTEs, etc.).\n"
                    "3) Use LQEL primitives only: where(...), groupby(...), calculate(...), limit(...), timeslice(...), "
                    "   and the case-insensitive helpers (istarts-with, icontains, nocase, regex /.../).\n"
                    "4) If the input includes concrete fields/values, apply them directly.\n"
                    "5) No explanations, no comments—just the code fence."
                ),
            ),
            ("human", "Convert this to LQEL:\n\n{bad_text}"),
        ]
    )
    return (prompt | llm | StrOutputParser())

# ------------------------ LCEL agent class ---------------------------

class LCELQueryAgent:
    """
    Decides per query whether to use retrieval:
      - If gate says YES -> call retrieval chain (self.qa_chain)
      - Else -> call direct chain (self.direct_chain)
    Enforces final output to be a single ```lqel``` block (auto-repairs SQL).
    """

    def __init__(
        self,
        qa_chain: Any,
        memory: Optional[ConversationBufferMemory] = None,
        prompt_template: Optional[str] = None,
    ):
        self.qa_chain = qa_chain
        self.memory = memory or ConversationBufferMemory(return_messages=True)
        self.prompt_template = prompt_template or DEFAULT_LCEL_TEMPLATE

        # IMPORTANT: do NOT bind temperature; some clients reject it.
        llm = get_default_doc_llm()

        # Direct (strict) LQEL chain
        direct_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "You are an LEQL (Log Expression Query Language) assistant.\n"
                        "Output STRICTLY one code block fenced as ```lqel``` containing the final query.\n"
                        # "ABSOLUTELY FORBIDDEN: SQL or SQL-like syntax (SELECT, FROM, JOIN, WITH, etc.).\n"
                        "and case-insensitive helpers (istarts-with, icontains, nocase, regex /.../).\n"
                        "No explanations or comments—only the fenced code."
                    ),
                ),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        self.direct_chain = (direct_prompt | llm | StrOutputParser())

        # Decision gate
        gate_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a decision gate. Answer strictly 'YES' or 'NO'.\n"
                    "Answer YES if retrieving saved LQEL examples would help "
                    "(user asks for examples/patterns/best practices or lacks specifics).\n"
                    "Answer NO for small edits/refinements of an existing query with concrete fields/values.",
                ),
                ("human", "Query: {query}"),
            ]
        )
        self.gate_chain = (gate_prompt | llm | StrOutputParser())

        # Repair chain (to convert any non-LQEL/SQL to LQEL)
        self.repair_chain = _build_repair_chain(llm)

        # Env overrides (optional)
        self.always_retrieve = os.getenv("LCEL_ALWAYS_RETRIEVE", "").lower() in ("1", "true", "yes")
        self.never_retrieve  = os.getenv("LCEL_NEVER_RETRIEVE",  "").lower() in ("1", "true", "yes")

    # ---------------------- decision logic ----------------------

    def _should_retrieve(self, query: str) -> bool:
        if self.always_retrieve:
            return True
        if self.never_retrieve:
            return False

        q = (query or "").strip().lower()
        has_tokens = any(tok in q for tok in ("lqel", "where(", "groupby(", "calculate(", "istarts-with"))
        mentions_edit = any(w in q for w in (" change ", " replace ", " modify ", " update "))

        if has_tokens and mentions_edit:
            return False

        try:
            ans = (self.gate_chain.invoke({"query": q}) or "").strip().upper()
            return ans.startswith("Y")
        except Exception:
            return not (has_tokens and len(q) > 40)

    # ---------------------- enforcement -------------------------

    def _enforce_lqel_once(self, text: str, history=None) -> str:
        # Already OK?
        if _looks_like_lqel(text) and not _looks_like_sql(text):
            block = _extract_lqel_block(text) or text
            return _wrap_as_lqel(block)

        # Try repair
        repaired = self.repair_chain.invoke({"bad_text": as_text(text)})
        block = _extract_lqel_block(repaired)
        if block and not _looks_like_sql(block):
            return _wrap_as_lqel(block)

        # Last resort: salvage
        for candidate in (text, repaired):
            blk = _extract_lqel_block(candidate or "")
            if blk and not _looks_like_sql(blk):
                return _wrap_as_lqel(blk)

        return "```lqel\n```"

    # ---------------------- public APIs -------------------------

    def handle_query_direct(self, query: str):
        try:
            hist = list(self.memory.chat_memory.messages)
            raw = self.direct_chain.invoke({"input": query, "chat_history": hist})
            text = self._enforce_lqel_once(raw, history=hist)
            self.memory.chat_memory.add_user_message(query)
            self.memory.chat_memory.add_ai_message(text)
            return {"text": text}
        except Exception as e:
            err = f"An error occurred while generating the query: {e}"
            self.memory.chat_memory.add_user_message(query)
            self.memory.chat_memory.add_ai_message(err)
            return {"text": err, "error": True}

    def handle_query(self, query: str):
        try:
            hist_msgs = list(self.memory.chat_memory.messages)
            if self._should_retrieve(query):
                raw = self.qa_chain.invoke({"input": query, "chat_history": hist_msgs})
                candidate = as_text(raw)
            else:
                candidate = self.direct_chain.invoke({"input": query, "chat_history": hist_msgs})

            text = self._enforce_lqel_once(candidate, history=hist_msgs)
            self.memory.chat_memory.add_user_message(query)
            self.memory.chat_memory.add_ai_message(text)
            return {"text": text}
        except Exception as e:
            err = f"An error occurred while processing the query: {e}"
            self.memory.chat_memory.add_user_message(query)
            self.memory.chat_memory.add_ai_message(err)
            return {"text": err, "error": True}
