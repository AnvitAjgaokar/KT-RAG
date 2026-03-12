from pathlib import Path


def parse_docx(file_path: str) -> list[dict]:
    """
    Extract text from a DOCX, splitting at heading boundaries into sections.
    Each section dict includes the heading name in metadata for precise citation.
    Falls back to docx2txt for legacy .doc files.
    Returns list of {text, metadata} dicts — one per section.
    """
    path = Path(file_path)

    if path.suffix.lower() == ".doc":
        return _parse_doc_fallback(file_path)

    from docx import Document

    doc = Document(file_path)

    # Walk body XML in document order so paragraphs and tables are interleaved correctly
    items = []  # list of ("heading"|"para", heading_level, text)
    for child in doc.element.body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":
            from docx.text.paragraph import Paragraph
            para = Paragraph(child, doc)
            text = para.text.strip()
            if not text:
                continue
            style = para.style.name
            if style.startswith("Heading"):
                level = int(style[-1]) if style[-1].isdigit() else 1
                items.append(("heading", level, text))
            else:
                items.append(("para", 0, text))

        elif tag == "tbl":
            from docx.table import Table
            table = Table(child, doc)
            for row in table.rows:
                row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    items.append(("para", 0, row_text))

    # Group items by heading sections
    sections = []
    current_heading = "Document Start"
    current_level = 0
    buffer = []

    def flush():
        text = "\n\n".join(buffer).strip()
        if text:
            sections.append({
                "text": text,
                "metadata": {
                    "source": path.name,
                    "file_path": str(file_path),
                    "file_type": "docx",
                    "section": current_heading,
                    "heading_level": current_level,
                    "page": len(sections) + 1,
                }
            })

    for kind, level, text in items:
        if kind == "heading":
            flush()
            current_heading = text
            current_level = level
            buffer = [f"## {text}"]
        else:
            buffer.append(text)

    flush()

    # Fallback: no headings found — return as a single section
    if not sections:
        all_text = "\n\n".join(t for _, _, t in items)
        if all_text:
            sections.append({
                "text": all_text,
                "metadata": {
                    "source": path.name,
                    "file_path": str(file_path),
                    "file_type": "docx",
                    "section": "Full Document",
                    "heading_level": 0,
                    "page": 1,
                }
            })

    return sections


def _parse_doc_fallback(file_path: str) -> list[dict]:
    """Use docx2txt to extract text from legacy .doc files."""
    import docx2txt
    text = docx2txt.process(file_path)
    if not text or not text.strip():
        return []
    return [{
        "text": text.strip(),
        "metadata": {
            "source": Path(file_path).name,
            "file_path": str(file_path),
            "file_type": "doc",
            "section": "Full Document",
            "heading_level": 0,
            "page": 1,
        }
    }]
