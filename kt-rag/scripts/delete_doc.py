#!/usr/bin/env python3
"""
Remove all vectorstore chunks for a specific document.
Usage: python scripts/delete_doc.py "filename.pdf"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import chromadb
from chromadb.config import Settings
from config import config
from rich.console import Console

console = Console()
COLLECTION_NAME = "kt_documents"


def main():
    if len(sys.argv) < 2:
        console.print("Usage: python scripts/delete_doc.py \"filename.pdf\"")
        sys.exit(1)

    filename = sys.argv[1]

    client = chromadb.PersistentClient(
        path=config.VECTORSTORE_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        console.print("[yellow]Vectorstore is empty or not yet created.[/yellow]")
        sys.exit(0)

    results = collection.get(where={"source": filename})
    count = len(results["ids"])

    if count == 0:
        console.print(f"[yellow]No chunks found for '{filename}'. Nothing deleted.[/yellow]")
        sys.exit(0)

    collection.delete(where={"source": filename})
    console.print(f"[bold green]Deleted {count} chunks for '{filename}' from vectorstore.[/bold green]")


if __name__ == "__main__":
    main()
