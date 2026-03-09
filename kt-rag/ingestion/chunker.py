import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import config


def _normalize(text: str) -> str:
    """Collapse excessive whitespace and strip leading/trailing blank lines."""
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def chunk_documents(docs: list[dict]) -> list[dict]:
    """
    Normalize, then split document sections into overlapping chunks.
    Prepends source name to each chunk for grounding context.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for doc in docs:
        clean_text = _normalize(doc["text"])
        if not clean_text:
            continue

        # Prepend source so every chunk is self-contained
        source_label = doc["metadata"].get("source", "")
        page = doc["metadata"].get("page", "")
        prefix = f"[From: {source_label}, p.{page}]\n" if source_label else ""
        labeled_text = prefix + clean_text

        text_chunks = splitter.split_text(labeled_text)
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
