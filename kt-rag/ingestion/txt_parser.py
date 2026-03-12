from pathlib import Path


def parse_txt(file_path: str) -> list[dict]:
    """Read a plain text file. Returns list of {text, metadata} dicts."""
    text = Path(file_path).read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    return [{
        "text": text,
        "metadata": {
            "source": Path(file_path).name,
            "file_path": str(file_path),
            "file_type": "txt",
            "page": 1
        }
    }]
