import re
import unicodedata
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pathlib import Path

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Minimum characters per page to consider it properly extracted (not scanned)
_MIN_TEXT_CHARS = 80


def _clean_text(text: str) -> str:
    """Remove PDF noise: repeated whitespace, page numbers, garbage lines."""
    # Normalize unicode (e.g. ligatures, smart quotes)
    text = unicodedata.normalize("NFKC", text)
    # Remove standalone page numbers (e.g. "  3  " or "Page 3 of 10")
    text = re.sub(r'(?m)^\s*(Page\s+\d+\s+(of\s+\d+)?|\d+)\s*$', '', text)
    # Collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse runs of spaces/tabs to a single space
    text = re.sub(r'[ \t]{2,}', ' ', text)
    # Remove lines that are purely symbols/noise (less than 3 real word chars)
    lines = [ln for ln in text.splitlines() if len(re.sub(r'\W', '', ln)) >= 3 or not ln.strip()]
    return "\n".join(lines).strip()


def _ocr_page(page) -> str:
    """Render a PDF page to image and OCR it as fallback."""
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    # Grayscale + slight upscale improves Tesseract accuracy
    img = img.convert("L")
    text = pytesseract.image_to_string(img, config="--psm 6")
    return text.strip()


def parse_pdf(file_path: str) -> list[dict]:
    """
    Extract text from each page of a PDF.
    Cleans noise, normalizes unicode, and falls back to OCR for scanned pages.
    Returns list of {text, metadata} dicts.
    """
    doc = fitz.open(file_path)
    pages = []
    ocr_fallback_count = 0

    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()

        # Fall back to OCR if page has too little text (likely scanned)
        if len(text) < _MIN_TEXT_CHARS:
            text = _ocr_page(page)
            if text:
                ocr_fallback_count += 1

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

    if ocr_fallback_count:
        print(f"    (OCR fallback used on {ocr_fallback_count} pages)")

    doc.close()
    return pages
