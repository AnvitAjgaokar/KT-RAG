from vectordb.store import get_vectorstore
from config import config

# Module-level vectorstore instance — initialized once, reused across all requests
_vectorstore = None


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore()
    return _vectorstore


def retrieve(query: str) -> list[dict]:
    """
    Fetch diverse top-K chunks using Maximal Marginal Relevance (MMR).
    MMR balances relevance with diversity, preventing redundant consecutive chunks
    from the same document flooding the LLM context window.
    Also runs a parallel similarity search to obtain scores for filtering and display.
    Returns list of {text, metadata, score} dicts.
    """
    vectorstore = _get_vectorstore()

    # MMR: fetch fetch_k candidates, select k most relevant AND diverse
    mmr_docs = vectorstore.max_marginal_relevance_search(
        query, k=config.TOP_K, fetch_k=config.TOP_K * 3
    )

    # Parallel similarity search for scores (used for threshold filter + display)
    scored = vectorstore.similarity_search_with_score(query, k=config.TOP_K)
    score_map = {doc.page_content[:120]: float(score) for doc, score in scored}

    retrieved = []
    for doc in mmr_docs:
        score = score_map.get(doc.page_content[:120], config.SCORE_THRESHOLD)
        print(f"  [retriever] score={score:.4f}  source={doc.metadata.get('source', '?')}")
        if score <= config.SCORE_THRESHOLD:
            retrieved.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "score": score
            })

    # Fallback: always return at least one result so the LLM can respond
    if not retrieved and mmr_docs:
        doc = mmr_docs[0]
        score = score_map.get(doc.page_content[:120], 0.5)
        retrieved.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })

    return retrieved
