import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Paths
    DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
    VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", "./vectorstore")

    # Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
    EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

    # Chunking
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

    # Retrieval
    TOP_K = int(os.getenv("TOP_K", "8"))
    SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "1.5"))

    # UI
    UI_HOST = os.getenv("UI_HOST", "0.0.0.0")
    UI_PORT = int(os.getenv("UI_PORT", "8000"))

config = Config()
