from langchain_ollama import OllamaEmbeddings
from config import config


def get_embedder():
    """
    Returns a LangChain-compatible Ollama embeddings object.
    Uses nomic-embed-text running locally.
    """
    return OllamaEmbeddings(
        model=config.EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL
    )
