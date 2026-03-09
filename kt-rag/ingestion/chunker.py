from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import config


def chunk_documents(docs: list[dict]) -> list[dict]:
    """
    Split document sections into overlapping chunks.
    Preserves and enriches metadata per chunk.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for doc in docs:
        text_chunks = splitter.split_text(doc["text"])
        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": i,
                    "total_chunks": len(text_chunks)
                }
            })

    print(f"✅ Created {len(chunks)} chunks from {len(docs)} document sections")
    return chunks
