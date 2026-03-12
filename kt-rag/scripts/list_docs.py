#!/usr/bin/env python3
"""
List all documents currently in the vectorstore with chunk counts and ingestion time.
Usage: python scripts/list_docs.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from collections import defaultdict
import chromadb
from chromadb.config import Settings
from config import config
from rich.console import Console
from rich.table import Table

console = Console()
COLLECTION_NAME = "kt_documents"


def main():
    client = chromadb.PersistentClient(
        path=config.VECTORSTORE_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        console.print("[yellow]Vectorstore is empty or not yet created. Run ingest.py first.[/yellow]")
        sys.exit(0)

    results = collection.get(include=["metadatas"])

    if not results["ids"]:
        console.print("[yellow]Vectorstore is empty.[/yellow]")
        sys.exit(0)

    stats = defaultdict(lambda: {"chunks": 0, "file_type": "?", "ingested_at": "unknown"})
    for meta in results["metadatas"]:
        src = meta.get("source", "Unknown")
        stats[src]["chunks"] += 1
        stats[src]["file_type"] = meta.get("file_type", "?").upper()
        if meta.get("ingested_at"):
            stats[src]["ingested_at"] = meta["ingested_at"]

    table = Table(title="Vectorstore Contents", show_lines=True)
    table.add_column("Document", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Chunks", justify="right")
    table.add_column("Last Ingested", style="dim")

    for src, info in sorted(stats.items()):
        table.add_row(src, info["file_type"], str(info["chunks"]), info["ingested_at"])

    console.print(table)
    console.print(f"\nTotal: [bold]{len(stats)}[/bold] documents, [bold]{len(results['ids'])}[/bold] chunks")


if __name__ == "__main__":
    main()
