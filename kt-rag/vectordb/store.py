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
    Skips duplicates using source+chunk_index as ID.
    """
    vectorstore = get_vectorstore()

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [
        f"{m['source']}__page{m.get('page', 0)}__chunk{m['chunk_index']}"
        for m in metadatas
    ]

    print(f"📥 Embedding {len(texts)} chunks into ChromaDB...")
    vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    print(f"✅ Stored {len(texts)} chunks in vectorstore at: {config.VECTORSTORE_DIR}")
