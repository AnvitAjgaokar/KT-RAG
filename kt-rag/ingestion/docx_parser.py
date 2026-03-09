from docx import Document
from pathlib import Path


def parse_docx(file_path: str) -> list[dict]:
    """
    Extract text from a DOCX file, preserving paragraph structure.
    Returns list of {text, metadata} dicts.
    """
    doc = Document(file_path)
    full_text = []

    for para in doc.paragraphs:
        if para.text.strip():
            full_text.append(para.text.strip())

    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                full_text.append(row_text)

    combined = "\n\n".join(full_text)
    return [{
        "text": combined,
        "metadata": {
            "source": Path(file_path).name,
            "file_path": str(file_path),
            "file_type": "docx",
            "page": 1
        }
    }]
