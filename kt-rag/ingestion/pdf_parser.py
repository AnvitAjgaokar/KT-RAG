import fitz  # PyMuPDF
from pathlib import Path


def parse_pdf(file_path: str) -> list[dict]:
    """
    Extract text from each page of a PDF.
    Returns list of {text, metadata} dicts.
    """
    doc = fitz.open(file_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({
                "text": text,
                "metadata": {
                    "source": Path(file_path).name,
                    "file_path": str(file_path),
                    "file_type": "pdf",
                    "page": page_num + 1,
                    "total_pages": len(doc)
                }
            })
    doc.close()
    return pages
