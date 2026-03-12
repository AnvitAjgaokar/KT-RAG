import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import config


def _normalize(text: str) -> str:
    """Collapse excessive whitespace and strip leading/trailing blank lines."""
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _build_prefix(metadata: dict) -> str:
    """
    Build a context prefix tailored to the file type.
    XLSX/XLS: sheet name + row range. DOCX: section heading. Others: filename + page.
    """
    source = metadata.get("source", "")
    if not source:
        return ""

    file_type = metadata.get("file_type", "")
    sheet = metadata.get("sheet", "")
    rows_start = metadata.get("rows_start", "")
    rows_end = metadata.get("rows_end", "")
    section = metadata.get("section", "")
    page = metadata.get("page", "")

    if file_type in ("xlsx", "xls") and sheet:
        if rows_start and rows_end:
            return f"[From: {source}, Sheet: {sheet}, Rows {rows_start}-{rows_end}]\n"
        return f"[From: {source}, Sheet: {sheet}]\n"

    if file_type in ("docx", "doc") and section and section != "Document Start":
        return f"[From: {source}, Section: {section}]\n"

    return f"[From: {source}, p.{page}]\n"


def chunk_documents(docs: list[dict]) -> list[dict]:
    """
    Normalize, then split document sections into overlapping chunks.
    Prepends a context-aware prefix to every chunk for grounding.
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

        prefix = _build_prefix(doc["metadata"])
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
