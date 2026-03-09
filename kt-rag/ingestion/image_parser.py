import pytesseract
from PIL import Image
from pathlib import Path

# On Windows, set this path if tesseract is not in PATH:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def parse_image(file_path: str) -> list[dict]:
    """
    OCR an image file and return extracted text.
    Returns list of {text, metadata} dicts.
    """
    img = Image.open(file_path)
    text = pytesseract.image_to_string(img).strip()

    if not text:
        return []

    return [{
        "text": text,
        "metadata": {
            "source": Path(file_path).name,
            "file_path": str(file_path),
            "file_type": "image",
            "page": 1
        }
    }]
