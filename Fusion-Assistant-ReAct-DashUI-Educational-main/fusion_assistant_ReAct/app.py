# fusion_assistant_ReAct/app.py
import os
from typing import Dict
from langchain import hub
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain.memory import ConversationBufferMemory

from .groups import GroupChatSystem
from .agents.lcel_agent import LCELQueryAgent
from .agents.asset_agent import Asset_Discovery_Agent
from .retrieval.vectorstores import build_or_load_all
from .retrieval.retrievers import build_retrievers_from_vectorstores
from .llm.models import get_default_doc_llm
from .react_agent import build_react_agent_executor
from .io.paths import DATASETS
from embeddings_oss import embeddings
from prompts import Doc_Analysis_prompt


def _build_chains_and_agents() -> Dict[str, object]:
    vs_map = build_or_load_all(DATASETS)
    retrievers = build_retrievers_from_vectorstores(vs_map)

    retrieval_qa_chat_prompt = hub.pull("langchain-ai/retrieval-qa-chat")
    doc_llm = get_default_doc_llm()

    combine_docs_chain = create_stuff_documents_chain(doc_llm, retrieval_qa_chat_prompt)

    lcel_chain  = create_retrieval_chain(retrievers["lcel"],  combine_docs_chain)
    asset_chain = create_retrieval_chain(retrievers["asset"], combine_docs_chain)

    lcel_agent    = LCELQueryAgent(lcel_chain, memory=ConversationBufferMemory(return_messages=True))
    asset_agent   = Asset_Discovery_Agent(asset_chain, memory=ConversationBufferMemory(return_messages=True))

    return {
        "doc_llm": doc_llm,
        "lcel": lcel_agent,
        "asset": asset_agent,
    }

_objs = _build_chains_and_agents()

react_executor = build_react_agent_executor(
    _objs["doc_llm"],
    # sigma_agent=_objs["sigma"],
    # log_agent=_objs["log"],
    # document_agent=_objs["summary"],
    lcel_agent=_objs["lcel"],
    asset_agent=_objs["asset"],
    memory=ConversationBufferMemory(return_messages=True),
)

def make_group() -> GroupChatSystem:
    return GroupChatSystem(react_executor)

def simulate_group_chat_and_store(group_chat: GroupChatSystem, json_file_path: str, query: str, fn=None, content=None):
    group_chat.add_message("User1", query)
    group_chat.query_agent(
        user="User1",
        store_path=json_file_path,
        message=query,
        content=content,
        fn=fn,
    )
## Store the conversation history