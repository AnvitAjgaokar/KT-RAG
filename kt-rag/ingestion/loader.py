from pathlib import Path
from ingestion.pdf_parser import parse_pdf
from ingestion.docx_parser import parse_docx
from ingestion.xlsx_parser import parse_xlsx
from ingestion.txt_parser import parse_txt

SUPPORTED_EXTENSIONS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".doc": parse_docx,
    ".xlsx": parse_xlsx,
    ".xls": parse_xlsx,
    ".txt": parse_txt,
}


def load_documents(docs_dir: str) -> list[dict]:
    """
    Walk docs_dir, parse all supported files.
    Returns flat list of {text, metadata} dicts.
    """
    docs_path = Path(docs_dir)
    all_docs = []

    for file_path in docs_path.rglob("*"):
        ext = file_path.suffix.lower()
        if ext in SUPPORTED_EXTENSIONS:
            print(f"  Loading: {file_path.name}")
            try:
                parser = SUPPORTED_EXTENSIONS[ext]
                docs = parser(str(file_path))
                all_docs.extend(docs)
            except Exception as e:
                print(f"  ⚠️  Failed to parse {file_path.name}: {e}")

    print(f"\n✅ Loaded {len(all_docs)} document sections from {docs_dir}")
    return all_docs
