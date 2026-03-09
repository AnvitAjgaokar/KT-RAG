import re
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# PSM modes to try: 6 = uniform block, 3 = auto, 4 = single column
_PSM_MODES = ["--psm 6", "--psm 3", "--psm 4"]


def _preprocess(img: Image.Image) -> Image.Image:
    """Convert to grayscale, boost contrast, upscale for better OCR."""
    img = img.convert("L")
    # Upscale small images — Tesseract works best at 300dpi equivalent
    w, h = img.size
    if w < 1200:
        scale = 1200 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    # Boost contrast
    img = ImageEnhance.Contrast(img).enhance(2.0)
    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    return img


def _clean_ocr(text: str) -> str:
    """Remove OCR garbage: stray symbols, repeated punctuation, empty lines."""
    # Remove lines with fewer than 3 alphanumeric characters
    lines = [ln for ln in text.splitlines() if len(re.sub(r'\W', '', ln)) >= 3 or not ln.strip()]
    text = "\n".join(lines)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def parse_image(file_path: str) -> list[dict]:
    """
    OCR an image with preprocessing and multiple PSM passes.
    Picks the longest (most complete) result.
    Returns list of {text, metadata} dicts.
    """
    img = Image.open(file_path)
    processed = _preprocess(img)

    best_text = ""
    for psm in _PSM_MODES:
        candidate = pytesseract.image_to_string(processed, config=psm).strip()
        if len(candidate) > len(best_text):
            best_text = candidate

    best_text = _clean_ocr(best_text)

    if not best_text:
        return []

    return [{
        "text": best_text,
        "metadata": {
            "source": Path(file_path).name,
            "file_path": str(file_path),
            "file_type": "image",
            "page": 1
        }
    }]
