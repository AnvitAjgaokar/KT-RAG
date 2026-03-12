#!/usr/bin/env python3
"""
Run this script to ingest all documents in the docs/ folder into ChromaDB.
Usage: python scripts/ingest.py
Re-running is safe — existing chunks are upserted (updated), not duplicated.
"""
import sys
import os
import urllib.request
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ingestion.loader import load_documents
from ingestion.chunker import chunk_documents
from vectordb.store import ingest_chunks
from config import config
from rich.console import Console
from rich.table import Table

console = Console()


def _check_ollama() -> bool:
    """Return True if the Ollama API is reachable."""
    try:
        urllib.request.urlopen(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        return True
    except Exception:
        return False


def main():
    console.print("\n[bold green]KT RAG — Document Ingestion Pipeline[/bold green]\n")
    console.print(f"Docs directory : {config.DOCS_DIR}")
    console.print(f"Vector store   : {config.VECTORSTORE_DIR}")
    console.print(f"Embed model    : {config.EMBED_MODEL}")
    console.print(f"Chunk size     : {config.CHUNK_SIZE} chars / overlap {config.CHUNK_OVERLAP}\n")

    # Pre-flight: verify Ollama is running before doing any work
    console.print("Checking Ollama connectivity...")
    if not _check_ollama():
        console.print(f"[bold red]Cannot reach Ollama at {config.OLLAMA_BASE_URL}[/bold red]")
        console.print("Please open the Ollama app from the Start Menu and try again.")
        sys.exit(1)
    console.print("[green]Ollama is running.[/green]\n")

    console.print("[bold]Step 1/3:[/bold] Loading documents...")
    docs = load_documents(config.DOCS_DIR)

    if not docs:
        console.print("[bold red]No documents found. Add files to the docs/ folder.[/bold red]")
        sys.exit(1)

    console.print("\n[bold]Step 2/3:[/bold] Chunking documents...")
    chunks = chunk_documents(docs)

    # Per-document stats
    stats = defaultdict(lambda: {"sections": 0, "chunks": 0, "chars": 0})
    for doc in docs:
        stats[doc["metadata"]["source"]]["sections"] += 1
        stats[doc["metadata"]["source"]]["chars"] += len(doc["text"])
    for chunk in chunks:
        stats[chunk["metadata"]["source"]]["chunks"] += 1

    table = Table(title="Ingestion Summary", show_lines=True)
    table.add_column("Document", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Sections", justify="right")
    table.add_column("Chunks", justify="right")
    table.add_column("Chars extracted", justify="right")

    for doc in docs:
        src = doc["metadata"]["source"]
        if src in stats:
            s = stats.pop(src)
            table.add_row(
                src,
                doc["metadata"].get("file_type", "?").upper(),
                str(s["sections"]),
                str(s["chunks"]),
                f"{s['chars']:,}"
            )

    console.print("\n[bold]Step 3/3:[/bold] Embedding & storing...")
    ingest_chunks(chunks)

    console.print()
    console.print(table)
    console.print(f"\n[bold green]Ingestion complete![/bold green] {len(chunks)} chunks stored.")
    console.print("Run the UI:  [bold]chainlit run ui\\app.py --host 0.0.0.0 --port 8000[/bold]")


if __name__ == "__main__":
    main()
