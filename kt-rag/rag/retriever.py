from vectordb.store import get_vectorstore
from config import config


def retrieve(query: str) -> list[dict]:
    """
    Embed query, find top-K similar chunks from ChromaDB.
    Returns list of {text, metadata, score} dicts.
    """
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=config.TOP_K)

    retrieved = []
    for doc, score in results:
        retrieved.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score)
        })
    return retrieved
