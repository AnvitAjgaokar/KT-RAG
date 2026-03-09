from vectordb.store import get_vectorstore
from config import config


def retrieve(query: str) -> list[dict]:
    """
    Embed query, fetch top-K similar chunks, filter by score threshold.
    Lower cosine distance = better match. Chunks above SCORE_THRESHOLD are discarded.
    Returns list of {text, metadata, score} dicts.
    """
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=config.TOP_K)

    retrieved = []
    for doc, score in results:
        score = float(score)
        print(f"  [retriever] score={score:.4f}  source={doc.metadata.get('source', '?')}")
        if score <= config.SCORE_THRESHOLD:
            retrieved.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            })

    if not retrieved:
        # Fallback: return best result even if above threshold, so LLM can respond
        if results:
            doc, score = results[0]
            retrieved.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })

    return retrieved
