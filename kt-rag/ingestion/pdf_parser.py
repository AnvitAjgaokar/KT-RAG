import re
import unicodedata
import fitz  # PyMuPDF
from pathlib import Path

# Minimum characters per page to consider it properly extracted (not scanned/blank)
_MIN_TEXT_CHARS = 80


def _clean_text(text: str) -> str:
    """Remove PDF noise: repeated whitespace, page numbers, garbage lines."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'(?m)^\s*(Page\s+\d+\s+(of\s+\d+)?|\d+)\s*$', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    lines = [ln for ln in text.splitlines() if len(re.sub(r'\W', '', ln)) >= 3 or not ln.strip()]
    return "\n".join(lines).strip()


def parse_pdf(file_path: str) -> list[dict]:
    """
    Extract text from each page of a PDF.
    Cleans noise and normalizes unicode.
    Pages with fewer than 80 characters (likely scanned or blank) are skipped.
    Returns list of {text, metadata} dicts — one per page.
    """
    doc = fitz.open(file_path)
    pages = []
    skipped = 0

    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()

        if len(text) < _MIN_TEXT_CHARS:
            skipped += 1
            continue

        text = _clean_text(text)
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

    if skipped:
        print(f"    (skipped {skipped} low-text pages — likely scanned or blank)")

    doc.close()
    return pages
