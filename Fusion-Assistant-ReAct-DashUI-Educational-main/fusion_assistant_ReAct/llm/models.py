"""
LLM factories and configuration with config-file support.
"""

from __future__ import annotations
import os
import yaml
from typing import Optional, Dict, Any

from langchain_ollama import ChatOllama


# ---------------- Load from config ----------------
def _load_config() -> Dict[str, Any]:
    config_path = os.getenv("CHAT_CONFIG", "fusion_assistant_ReAct/config/model_config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


_config = _load_config()


def build_chat_model(
    name: Optional[str] = None,
    *,
    temperature: Optional[float] = None,
    **kwargs,
):
    """
    Return a ChatOllama instance.
    Precedence order:
      1. Direct kwargs
      2. Explicit args (name, temperature)
      3. Config file values
      4. Environment variables
      5. Defaults
    """
    model_name = (
        name
        or kwargs.pop("model_name", None)
        or _config.get("model_name")
        or os.getenv("CHAT_MODEL_NAME", "gpt-oss:20b")
    )
    temp = (
        temperature
        if temperature is not None
        else kwargs.pop("temperature", None)
        or _config.get("temperature")
        or float(os.getenv("CHAT_TEMPERATURE", "0.0"))
    )

    # Collect model_kwargs from config
    model_kwargs = dict(_config)
    for drop in ["model_name", "temperature", "base_url"]:
        model_kwargs.pop(drop, None)

    # Merge with passed kwargs (explicit > config)
    if "model_kwargs" in kwargs:
        model_kwargs.update(kwargs.pop("model_kwargs"))

    merged_kwargs = {**model_kwargs, **kwargs}
    print(f"[LLM] Using model: {model_name}, temp={temp}, kwargs={merged_kwargs}")

    return ChatOllama(
        model=model_name,
        temperature=float(temp),
        # num_predict=256,
        base_url=_config.get("base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")),
        model_kwargs=model_kwargs or None,
        **kwargs,
    )


def get_default_doc_llm():
    return build_chat_model()
