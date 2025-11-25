# fusion_assistant_ReAct/react_agent.py
from __future__ import annotations
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain_core.callbacks import BaseCallbackHandler

# NEW: pull configured paths so the asset tool can run from backend config
from .io import paths  # provides ASSET_DIR, DRAFT_CHECKPOINT


# --------------------------- Debug callbacks ---------------------------

class PrintLLMHandler(BaseCallbackHandler):
    def on_llm_end(self, result, **k):
        try:
            gens = result.generations or []
            if gens and gens[0] and gens[0][0].text:
                print("\n--- RAW LLM OUTPUT (last) ---")
                print(gens[0][0].text)
                print("--- END RAW LLM OUTPUT ---\n")
        except Exception:
            pass

class DebugToolHandler(BaseCallbackHandler):
    def on_tool_start(self, tool, input_str, **kwargs):
        print(f"\n[TOOL START] {tool} ← input: {input_str}\n")
    def on_tool_end(self, output, **kwargs):
        print(f"\n[TOOL END] output (truncated): {str(output)[:400]}\n")


# --------------------------- Utilities ---------------------------

class ToolInput(BaseModel):
    """Arguments passed to each tool by the ReAct agent."""
    query: str = Field(..., description="User question or instruction.")
    context: Optional[str] = Field(None, description="Active document text, if any.")
    filename: Optional[str] = Field(None, description="Active document filename, if any.")

def _as_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        for k in ("answer", "text", "output_text", "content", "result", "output"):
            v = x.get(k)
            if isinstance(v, str):
                return v
        import json
        return json.dumps(x, ensure_ascii=False, indent=2)
    if hasattr(x, "content") and isinstance(getattr(x, "content"), str):
        return x.content
    return str(x)

def _mk_tool(name: str, description: str, handler, *, return_direct: bool = False):
    def _run(payload: Dict[str, Any]) -> str:
        print(f"[TOOL {name}] invoked with payload: {payload}")
        if isinstance(payload, str):
            return _as_text(handler(payload, None, None))
        q = payload.get("query", "")
        ctx = payload.get("context")
        fn = payload.get("filename")
        return _as_text(handler(q, ctx, fn))
    return Tool(
        name=name,
        description=description.strip(),
        func=_run,
        args_schema=ToolInput,
        return_direct=return_direct,
    )


# --------------------------- STRICT ReAct Prompt ---------------------------

REACT_PROMPT = PromptTemplate.from_template(
"""You are a precise ReAct agent that selects the best tool and responds ONLY in valid ReAct format.

Available tools:
{tools}

The tool names you can choose from are: {tool_names}.

The conversation input is structured as:
- "User query:" <user message>
- "Active document filename:" <filename or 'None'>
- "Active document text:" <full text or empty>

### RULES (follow EXACTLY)
- Do NOT repeat the user's question back as your answer.
- If you need a tool, output EXACTLY:
  Thought: <brief reason for choosing ONE tool>
  Action: <ONE name from {tool_names}>
  Action Input: {{"query": "<copy the user's question>", "context": "<full doc text or null>", "filename": "<filename or null>"}}
  After you output the line starting with `Action Input: {{...}}`, OUTPUT NOTHING ELSE.

- AFTER YOU SEE AN OBSERVATION FROM A TOOL, YOU MUST FINISH:
  Output EXACTLY:
  Final Answer: <paste the Observation content verbatim or a concise rendering of it>

- If no tool is needed, output EXACTLY:
  Thought: <brief reason a tool is unnecessary>
  Final Answer: <your final answer>

- Call at most ONE tool unless absolutely necessary.

Question: {input}
{agent_scratchpad}
"""
)


# --------------------------- Builder ---------------------------

def build_react_agent_executor(
    llm,
    *,
    lcel_agent,
    asset_agent,
    memory: Optional[ConversationBufferMemory] = None,
) -> AgentExecutor:
    """
    Wrap your existing agents behind ReAct tools and return an AgentExecutor.
    """

    # --- Adapters: map tool call -> your agent functions ---
    def _lcel_handle(query: str, context: Optional[str], filename: Optional[str]):
        return lcel_agent.handle_query(query)

    def _asset_handle(query: str, context: Optional[str], filename: Optional[str]):
        """
        Behavior:
        - If context is JSON (single asset dict), generate ONE draft body for that record.
        - Otherwise, run a full "assets drafting run" from backend config:
            * reads JSONL(s) under paths.ASSET_DIR
            * writes to paths.DRAFT_CHECKPOINT
            * returns a concise text report (counts, checkpoint path, sample subjects)
        """
        # Try single-record mode first (JSON in context)
        try:
            import json
            if context:
                data = json.loads(context)
                if isinstance(data, dict):
                    return asset_agent.handle_query(data)
                # If user passed a list, draft only the first and say how many were provided.
                if isinstance(data, list) and data:
                    single = asset_agent.handle_query(data[0])
                    body = _as_text(single)
                    return {
                        "answer": f"Drafted first of {len(data)} records from JSON list.\n\n{body}"
                    }
        except Exception:
            pass

        # Batch-from-config mode
        subject_template = "Asset Review: {hostname}"
        report = asset_agent.run_from_config(
            asset_dir=paths.ASSET_DIR,
            checkpoint_path=paths.DRAFT_CHECKPOINT,
            subject_template=subject_template,
            run_id=None,
            max_preview=8,   # show a few subjects inline
        )
        return {"answer": report}

    # --- Tools ---
    tools = [
        _mk_tool("lcel_query_planner",
                 "Generate an LCEL/LQEL expression or query plan.",
                 _lcel_handle, return_direct=True),
        _mk_tool("asset_discovery_ops",
                 "Draft asset-owner emails. If a JSON asset is given in context, draft one. Otherwise, draft from backend-configured JSONL directory and return a concise report.",
                 _asset_handle, return_direct=True),
    ]

    # Respect stop tokens coming from your model config (you already bind them in your LLM)
    stop_tokens = [
        "\nObservation:",
        "\nFinal Answer:",
        "Observation:",
        "Final Answer:",
    ]
    llm_bound = getattr(llm, "bind", lambda **kw: llm)(stop=stop_tokens)

    mem = memory or ConversationBufferMemory(return_messages=True)
    agent = create_react_agent(llm=llm_bound, tools=tools, prompt=REACT_PROMPT)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=mem,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
        early_stopping_method="force",
        return_intermediate_steps=True,
        callbacks=[PrintLLMHandler(), DebugToolHandler()],
    )
    return executor
