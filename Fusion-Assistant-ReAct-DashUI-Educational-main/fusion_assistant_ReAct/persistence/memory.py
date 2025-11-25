import os
from langchain.vectorstores import FAISS
from langchain.schema import Document

def init_or_load_faiss(path: str, embedding_model):
    index_faiss = os.path.join(path, "index.faiss")
    index_pkl = os.path.join(path, "index.pkl")
    if os.path.exists(index_faiss) and os.path.exists(index_pkl):
        return FAISS.load_local(folder_path=path, embeddings=embedding_model, allow_dangerous_deserialization=True)
    os.makedirs(path, exist_ok=True)
    dummy = Document(page_content="This is a placeholder.", metadata={"source": "init"})
    store = FAISS.from_documents([dummy], embedding_model)
    store.save_local(path)
    # keep a convenient attribute for log_agent
    store.folder_path = path
    return store
