# fusion_assistant_ReAct/groups.py
from typing import Any, Dict, List, Optional
import json
from langchain.schema import Document
from .persistence.chat_history import store_chatHist, documents_to_json_serializable

def _as_text(resp: Any) -> str:
    if resp is None:
        return ""
    if isinstance(resp, str):
        return resp
    if isinstance(resp, dict):
        for k in ("text", "answer", "result", "output_text", "content", "output"):
            v = resp.get(k)
            if isinstance(v, str):
                return v
        return json.dumps(resp, indent=2, ensure_ascii=False)
    if isinstance(resp, list) and all(isinstance(x, str) for x in resp):
        return "\n".join(resp)
    return str(resp)

class GroupChatSystem:
    def __init__(self, executor):
        """
        executor: LangChain AgentExecutor (ReAct) that decides which tool to call.
        """
        self.executor = executor
        self.chat_history: List[Dict[str, Any]] = []

    def add_message(self, user, message):
        self.chat_history.append({"user": user, "message": message})
        print(f"{user}: {message}")

    def _pack_input(self, message: str, content: Optional[str], fn: Optional[str]) -> str:
        """
        Provide the active document to the ReAct agent in a structured way so it
        can include it in tool calls as JSON.
        """
        doc_name = fn or "None"
        doc_text = (content or "").strip()
        packed = (
            "User query:\n"
            f"{message}\n\n"
            f"Active document filename: {doc_name}\n"
            "Active document text (may be empty below):\n"
            f"{doc_text}"
        )
        return packed

    def query_agent(self, user: str, store_path: str, message: str, content: Optional[str]=None, fn: Optional[str]=None):
        # 1) record message
        self.add_message(user, message)

        # 2) call ReAct agent (returns dict like {"output": "...", ...})
        packed_input = self._pack_input(message, content, fn)
        result = self.executor.invoke({"input": packed_input})
        # DEBUG: dump the ReAct scratchpad / steps
        steps = result.get("intermediate_steps", [])
        if steps:
            print("\n=== INTERMEDIATE STEPS ===")
            for i, (agent_action, observation) in enumerate(steps, 1):
                try:
                    print(f"\nStep {i}")
                    print("  Thought:", getattr(agent_action, "log", "").split("Action:")[0].strip())
                    print("  Action:", getattr(agent_action, "tool", ""))
                    print("  Action Input:", getattr(agent_action, "tool_input", ""))
                    print("  Observation:", observation)
                except Exception:
                    print("  Raw agent_action:", agent_action)
                    print("  Raw observation:", observation)
            print("=== END STEPS ===\n")
        else:
            print("[DEBUG] No intermediate_steps returned (likely no valid Action parsed).")
        response_text = _as_text(result.get("output", result))

        # 3) persist history
        if content is None and fn is None:
            store_chatHist(message, response_text, None, store_path)
        else:
            meta_doc = documents_to_json_serializable([Document(page_content=content or "", metadata={"filename": fn or ""})])
            store_chatHist(message, response_text, meta_doc, store_path)

        # 4) append assistant message
        self.chat_history.append({"user": "Assistant", "message": response_text})
        print(f"Assistant: {response_text}")
