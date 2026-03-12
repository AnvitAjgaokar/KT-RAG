import hashlib
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from embeddings.embedder import get_embedder
from config import config

COLLECTION_NAME = "kt_documents"


def get_vectorstore(readonly: bool = False):
    """
    Returns a LangChain Chroma vectorstore backed by local persistent storage.
    """
    client = chromadb.PersistentClient(
        path=config.VECTORSTORE_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embedder()
    )


def ingest_chunks(chunks: list[dict]):
    """
    Embed and store all chunks into ChromaDB.
    Uses upsert so re-running is safe — existing chunks are updated, not duplicated.
    """
    vectorstore = get_vectorstore()
    embedder = get_embedder()

    from datetime import datetime
    ingested_at = datetime.utcnow().isoformat()

    texts = [c["text"] for c in chunks]
    metadatas = [{**c["metadata"], "ingested_at": ingested_at} for c in chunks]
    ids = []
    for m in metadatas:
        # Build a unique key using source, sheet (if xlsx), page, and chunk index
        sheet = m.get('sheet', '')
        source = m['source']
        page = m.get('page', 0)
        chunk_idx = m['chunk_index']
        raw_id = f"{source}__{sheet}__page{page}__chunk{chunk_idx}"
        # Hash to ensure valid ChromaDB ID (no special chars issues)
        short_hash = hashlib.md5(raw_id.encode()).hexdigest()[:12]
        ids.append(f"{source}__p{page}_c{chunk_idx}_{short_hash}")

    print(f"📥 Embedding {len(texts)} chunks into ChromaDB...")

    # Use upsert in batches to avoid duplicate ID errors on re-runs
    BATCH_SIZE = 50
    for start in range(0, len(texts), BATCH_SIZE):
        end = min(start + BATCH_SIZE, len(texts))
        batch_texts = texts[start:end]
        batch_metadatas = metadatas[start:end]
        batch_ids = ids[start:end]
        batch_embeddings = embedder.embed_documents(batch_texts)

        collection = vectorstore._collection
        collection.upsert(
            documents=batch_texts,
            metadatas=batch_metadatas,
            ids=batch_ids,
            embeddings=batch_embeddings,
        )
        print(f"  ✅ Upserted batch {start // BATCH_SIZE + 1} ({end}/{len(texts)})")

    print(f"✅ Stored {len(texts)} chunks in vectorstore at: {config.VECTORSTORE_DIR}")
