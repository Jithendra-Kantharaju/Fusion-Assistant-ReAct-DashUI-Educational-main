# embeddings_oss.py
from langchain_community.embeddings import HuggingFaceEmbeddings

# Small, fast, OSS sentence-transformer
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    # encode_kwargs={"normalize_embeddings": True},  # optional
)
