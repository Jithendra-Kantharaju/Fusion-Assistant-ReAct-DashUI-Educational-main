import tiktoken
def count_tokens(prompt: str, model_used: str = "gpt-4o") -> int:
    enc = tiktoken.encoding_for_model(model_used)
    return len(enc.encode(prompt or ""))
