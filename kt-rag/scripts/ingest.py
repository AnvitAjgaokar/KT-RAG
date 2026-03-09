#!/usr/bin/env python3
"""
Run this script to ingest all documents in the docs/ folder into ChromaDB.
Usage: python scripts/ingest.py
Re-running is safe -- duplicate chunks are skipped by ID.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ingestion.loader import load_documents
from ingestion.chunker import chunk_documents
from vectordb.store import ingest_chunks
from config import config
from rich.console import Console

console = Console()


def main():
    console.print("\n[bold green]KT RAG -- Document Ingestion Pipeline[/bold green]\n")
    console.print(f"Docs directory : {config.DOCS_DIR}")
    console.print(f"Vector store   : {config.VECTORSTORE_DIR}")
    console.print(f"Embed model    : {config.EMBED_MODEL}\n")

    console.print("[bold]Step 1/3:[/bold] Loading documents...")
    docs = load_documents(config.DOCS_DIR)

    console.print("\n[bold]Step 2/3:[/bold] Chunking documents...")
    chunks = chunk_documents(docs)

    console.print("\n[bold]Step 3/3:[/bold] Embedding & storing...")
    ingest_chunks(chunks)

    console.print("\n[bold green]Ingestion complete! Run the UI to start querying.[/bold green]")


if __name__ == "__main__":
    main()
