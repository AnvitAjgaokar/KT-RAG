# 🧠 Local RAG System — Knowledge Transfer Docs
## Claude Code Build Specification

> **Purpose**: Build a fully local, offline RAG (Retrieval-Augmented Generation) system that lets team members query Knowledge Transfer documents (PDFs, DOCX, images) via a chat interface. Zero cloud dependency. Deployable on an office local machine (Linux/Windows).

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Phase 1 — Document Ingestion Pipeline](#phase-1--document-ingestion-pipeline)
5. [Phase 2 — Embedding & Vector Store](#phase-2--embedding--vector-store)
6. [Phase 3 — Query & RAG Pipeline](#phase-3--query--rag-pipeline)
7. [Phase 4 — Chat UI (Chainlit)](#phase-4--chat-ui-chainlit)
8. [Phase 5 — Local Machine Deployment](#phase-5--local-machine-deployment)
9. [Configuration & Environment](#configuration--environment)
10. [Testing Checklist](#testing-checklist)
11. [Troubleshooting Guide](#troubleshooting-guide)

---

## Project Overview

### What to Build
A CLI + Web-based RAG system with:
- **Ingestion script**: Parses KT documents (PDF, DOCX, PNG/JPG) → chunks → embeds → stores in local ChromaDB
- **Query engine**: Takes user question → embeds → similarity search → builds prompt → local LLM answers
- **Chat UI**: Chainlit-based web interface accessible via browser on local network
- **Deployment**: Runs as a persistent service on an office Linux/Windows machine

### Constraints
- ✅ 100% offline — no OpenAI, no cloud APIs
- ✅ All models run locally via Ollama
- ✅ All data stays on the office machine
- ✅ Accessible to all teammates via LAN (e.g., `http://192.168.x.x:8000`)
- ✅ Easy to add new documents later

---

## Tech Stack

| Layer | Tool | Version | Notes |
|---|---|---|---|
| Language | Python | 3.11+ | Use `pyenv` if needed |
| LLM runner | Ollama | Latest | Manages local models |
| LLM model | `llama3.2` or `mistral` | 7B | Pick based on RAM |
| Embedding model | `nomic-embed-text` | via Ollama | Local embeddings |
| RAG framework | LangChain | `>=0.2` | Orchestration |
| Vector DB | ChromaDB | `>=0.5` | Local persistent store |
| PDF parser | PyMuPDF (`fitz`) | Latest | Best text extraction |
| DOCX parser | python-docx | Latest | Word doc parsing |
| OCR (images) | Tesseract + pytesseract | Latest | For image/scanned docs |
| Chat UI | Chainlit | Latest | Browser-based chat |
| Process manager | PM2 or systemd | — | Keep app alive on server |

---

## Project Structure

```
kt-rag/
├── README.md
├── requirements.txt
├── .env                        # Config: paths, model names, ports
├── config.py                   # Loads .env, central config object
│
├── docs/                       # ← PUT ALL KT DOCUMENTS HERE
│   ├── pdf/
│   ├── docx/
│   └── images/
│
├── vectorstore/                # Auto-created: ChromaDB persisted data
│
├── ingestion/
│   ├── __init__.py
│   ├── loader.py               # Detects file type, routes to parser
│   ├── pdf_parser.py           # PyMuPDF PDF → text
│   ├── docx_parser.py          # python-docx DOCX → text
│   ├── image_parser.py         # Tesseract OCR image → text
│   └── chunker.py              # Text → overlapping chunks with metadata
│
├── embeddings/
│   ├── __init__.py
│   └── embedder.py             # Wraps Ollama nomic-embed-text
│
├── vectordb/
│   ├── __init__.py
│   └── store.py                # ChromaDB init, upsert, query
│
├── rag/
│   ├── __init__.py
│   ├── retriever.py            # Similarity search, top-K fetch
│   └── chain.py                # Prompt template + LLM chain
│
├── ui/
│   └── app.py                  # Chainlit chat application
│
├── scripts/
│   ├── ingest.py               # CLI: run ingestion pipeline
│   └── query.py                # CLI: test query without UI
│
└── deploy/
    ├── kt-rag.service          # systemd service file (Linux)
    ├── Dockerfile              # Optional Docker packaging
    ├── docker-compose.yml      # Optional: app + ollama in containers
    └── setup_server.sh         # One-shot server setup script
```

---

## Phase 1 — Document Ingestion Pipeline

### 1.1 `requirements.txt`
Create this file first. Install with `pip install -r requirements.txt`.

```
langchain>=0.2.0
langchain-community>=0.2.0
langchain-ollama>=0.1.0
chromadb>=0.5.0
PyMuPDF>=1.24.0
python-docx>=1.1.0
pytesseract>=0.3.10
Pillow>=10.0.0
chainlit>=1.0.0
python-dotenv>=1.0.0
unstructured>=0.14.0
rich>=13.0.0
```

### 1.2 `config.py`
```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Paths
    DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
    VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", "./vectorstore")

    # Ollama
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
    EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

    # Chunking
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

    # Retrieval
    TOP_K = int(os.getenv("TOP_K", "5"))

    # UI
    UI_HOST = os.getenv("UI_HOST", "0.0.0.0")   # 0.0.0.0 = accessible on LAN
    UI_PORT = int(os.getenv("UI_PORT", "8000"))

config = Config()
```

### 1.3 `.env`
```env
DOCS_DIR=./docs
VECTORSTORE_DIR=./vectorstore
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
EMBED_MODEL=nomic-embed-text
CHUNK_SIZE=800
CHUNK_OVERLAP=150
TOP_K=5
UI_HOST=0.0.0.0
UI_PORT=8000
```

### 1.4 `ingestion/pdf_parser.py`
```python
import fitz  # PyMuPDF
from pathlib import Path

def parse_pdf(file_path: str) -> list[dict]:
    """
    Extract text from each page of a PDF.
    Returns list of {text, metadata} dicts.
    """
    doc = fitz.open(file_path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({
                "text": text,
                "metadata": {
                    "source": Path(file_path).name,
                    "file_path": str(file_path),
                    "file_type": "pdf",
                    "page": page_num + 1,
                    "total_pages": len(doc)
                }
            })
    doc.close()
    return pages
```

### 1.5 `ingestion/docx_parser.py`
```python
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
```

### 1.6 `ingestion/image_parser.py`
```python
import pytesseract
from PIL import Image
from pathlib import Path

# On Windows, set this path if tesseract is not in PATH:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
```

### 1.7 `ingestion/loader.py`
```python
from pathlib import Path
from ingestion.pdf_parser import parse_pdf
from ingestion.docx_parser import parse_docx
from ingestion.image_parser import parse_image

SUPPORTED_EXTENSIONS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".doc": parse_docx,
    ".png": parse_image,
    ".jpg": parse_image,
    ".jpeg": parse_image,
    ".tiff": parse_image,
    ".bmp": parse_image,
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
```

### 1.8 `ingestion/chunker.py`
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import config

def chunk_documents(docs: list[dict]) -> list[dict]:
    """
    Split document sections into overlapping chunks.
    Preserves and enriches metadata per chunk.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for doc in docs:
        text_chunks = splitter.split_text(doc["text"])
        for i, chunk_text in enumerate(text_chunks):
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": i,
                    "total_chunks": len(text_chunks)
                }
            })

    print(f"✅ Created {len(chunks)} chunks from {len(docs)} document sections")
    return chunks
```

---

## Phase 2 — Embedding & Vector Store

### 2.1 `embeddings/embedder.py`
```python
from langchain_ollama import OllamaEmbeddings
from config import config

def get_embedder():
    """
    Returns a LangChain-compatible Ollama embeddings object.
    Uses nomic-embed-text running locally.
    """
    return OllamaEmbeddings(
        model=config.EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL
    )
```

### 2.2 `vectordb/store.py`
```python
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from embeddings.embedder import get_embedder
from config import config

COLLECTION_NAME = "kt_documents"

def get_vectorstore(readonly: bool = False):
    """
    Returns a LangChain Chroma vectorstore backed by local persistent storage.
    """
    client = chromadb.PersistentClient(
        path=config.VECTORSTORE_DIR,
        settings=Settings(anonymized_telemetry=False)
    )

    return Chroma(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding_function=get_embedder()
    )

def ingest_chunks(chunks: list[dict]):
    """
    Embed and store all chunks into ChromaDB.
    Skips duplicates using source+chunk_index as ID.
    """
    vectorstore = get_vectorstore()

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [
        f"{m['source']}__page{m.get('page', 0)}__chunk{m['chunk_index']}"
        for m in metadatas
    ]

    print(f"📥 Embedding {len(texts)} chunks into ChromaDB...")
    vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    print(f"✅ Stored {len(texts)} chunks in vectorstore at: {config.VECTORSTORE_DIR}")
```

---

## Phase 3 — Query & RAG Pipeline

### 3.1 `rag/retriever.py`
```python
from vectordb.store import get_vectorstore
from config import config

def retrieve(query: str) -> list[dict]:
    """
    Embed query, find top-K similar chunks from ChromaDB.
    Returns list of {text, metadata, score} dicts.
    """
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_score(query, k=config.TOP_K)

    retrieved = []
    for doc, score in results:
        retrieved.append({
            "text": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score)
        })
    return retrieved
```

### 3.2 `rag/chain.py`
```python
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from rag.retriever import retrieve
from config import config

# System prompt — tune this to your team's context
PROMPT_TEMPLATE = """You are a helpful assistant for a software development team.
You answer questions based ONLY on the Knowledge Transfer documents provided below.
If the answer is not in the documents, say "I don't have that information in the KT docs."
Always mention which document/file the information came from.

--- KNOWLEDGE BASE CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Answer (cite source document names):"""

prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=PROMPT_TEMPLATE
)

def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into readable context block."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        source = meta.get("source", "Unknown")
        page = meta.get("page", "?")
        parts.append(f"[Source {i}: {source}, Page {page}]\n{chunk['text']}")
    return "\n\n".join(parts)

def answer(question: str) -> dict:
    """
    Full RAG pipeline: retrieve → build context → LLM answer.
    Returns {answer, sources} dict.
    """
    chunks = retrieve(question)
    context = build_context(chunks)

    llm = OllamaLLM(
        model=config.LLM_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=0.1   # Low temp = factual, less creative
    )

    chain = prompt | llm
    response = chain.invoke({"context": context, "question": question})

    # Deduplicate sources for display
    sources = list({
        f"{c['metadata'].get('source', 'Unknown')} (p.{c['metadata'].get('page', '?')})"
        for c in chunks
    })

    return {
        "answer": response,
        "sources": sources,
        "chunks_used": len(chunks)
    }
```

---

## Phase 4 — Chat UI (Chainlit)

### 4.1 `ui/app.py`
```python
import chainlit as cl
from rag.chain import answer

@cl.on_chat_start
async def on_start():
    await cl.Message(
        content=(
            "👋 **Welcome to the KT Knowledge Base!**\n\n"
            "Ask me anything about the project — architecture, setup, processes, APIs, "
            "deployment, or any topic covered in the Knowledge Transfer documents.\n\n"
            "I'll answer based only on the KT docs and tell you exactly which document "
            "the information came from."
        )
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    question = message.content.strip()

    # Show thinking indicator
    async with cl.Step(name="🔍 Searching KT documents...") as step:
        result = answer(question)
        step.output = f"Found {result['chunks_used']} relevant sections"

    # Format sources as footer
    sources_text = "\n".join(f"  - 📄 {s}" for s in result["sources"])
    full_response = (
        f"{result['answer']}\n\n"
        f"---\n**Sources used:**\n{sources_text}"
    )

    await cl.Message(content=full_response).send()
```

### 4.2 Run the UI
```bash
# From project root:
chainlit run ui/app.py --host 0.0.0.0 --port 8000
```

---

## CLI Scripts

### `scripts/ingest.py`
```python
#!/usr/bin/env python3
"""
Run this script to ingest all documents in the docs/ folder into ChromaDB.
Usage: python scripts/ingest.py
Re-running is safe — duplicate chunks are skipped by ID.
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
    console.print("\n[bold green]🚀 KT RAG — Document Ingestion Pipeline[/bold green]\n")
    console.print(f"📁 Docs directory : {config.DOCS_DIR}")
    console.print(f"🗄️  Vector store   : {config.VECTORSTORE_DIR}")
    console.print(f"🤖 Embed model    : {config.EMBED_MODEL}\n")

    console.print("[bold]Step 1/3:[/bold] Loading documents...")
    docs = load_documents(config.DOCS_DIR)

    console.print("\n[bold]Step 2/3:[/bold] Chunking documents...")
    chunks = chunk_documents(docs)

    console.print("\n[bold]Step 3/3:[/bold] Embedding & storing...")
    ingest_chunks(chunks)

    console.print("\n[bold green]✅ Ingestion complete! Run the UI to start querying.[/bold green]")

if __name__ == "__main__":
    main()
```

### `scripts/query.py`
```python
#!/usr/bin/env python3
"""
CLI test for the RAG pipeline without starting the UI.
Usage: python scripts/query.py "How do I deploy the auth service?"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rag.chain import answer

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/query.py \"your question here\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\n❓ Question: {question}\n")
    print("⏳ Thinking...\n")

    result = answer(question)
    print(f"💬 Answer:\n{result['answer']}\n")
    print(f"📄 Sources: {', '.join(result['sources'])}")

if __name__ == "__main__":
    main()
```

---

## Phase 5 — Local Machine Deployment

### 5.1 Prerequisites — Office Machine Setup

#### Linux (Ubuntu/Debian) — Recommended
```bash
# 1. Install Python 3.11+
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip

# 2. Install Tesseract OCR
sudo apt install -y tesseract-ocr tesseract-ocr-eng

# 3. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 4. Pull required models (run once, downloads ~4-8GB)
ollama pull llama3.2
ollama pull nomic-embed-text

# 5. Verify Ollama is running
ollama list
```

#### Windows (Office PC)
```powershell
# 1. Install Python 3.11+ from https://python.org
# 2. Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
#    → Note the install path (e.g. C:\Program Files\Tesseract-OCR\)
# 3. Install Ollama from https://ollama.com/download/windows
# 4. Open PowerShell:
ollama pull llama3.2
ollama pull nomic-embed-text
```

### 5.2 Project Setup (Both OS)
```bash
# Clone or copy the project to the server
git clone <your-repo> kt-rag
cd kt-rag

# Create virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Add your KT documents
cp /path/to/your/docs/* ./docs/

# Run ingestion
python scripts/ingest.py

# Test a query
python scripts/query.py "What is the deployment process?"

# Launch UI (accessible on LAN)
chainlit run ui/app.py --host 0.0.0.0 --port 8000
```

Users on the same network can now access: `http://<office-machine-ip>:8000`

---

### 5.3 Keep it Running — systemd Service (Linux)

#### `deploy/kt-rag.service`
```ini
[Unit]
Description=KT RAG Knowledge Base
After=network.target ollama.service

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/kt-rag
Environment="PATH=/home/YOUR_USERNAME/kt-rag/venv/bin"
ExecStart=/home/YOUR_USERNAME/kt-rag/venv/bin/chainlit run ui/app.py --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Install the service (replace YOUR_USERNAME)
sudo cp deploy/kt-rag.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable kt-rag
sudo systemctl start kt-rag

# Check status
sudo systemctl status kt-rag

# View logs
journalctl -u kt-rag -f
```

---

### 5.4 Keep it Running — Windows (Task Scheduler or NSSM)

#### Option A: NSSM (Non-Sucking Service Manager) — Recommended
```powershell
# 1. Download NSSM from https://nssm.cc
# 2. Open PowerShell as Administrator
nssm install KT-RAG "C:\kt-rag\venv\Scripts\chainlit.exe"
nssm set KT-RAG Arguments "run ui/app.py --host 0.0.0.0 --port 8000"
nssm set KT-RAG AppDirectory "C:\kt-rag"
nssm start KT-RAG
```

#### Option B: Startup batch script
```bat
@echo off
:: save as start_kt_rag.bat, add to Windows Task Scheduler → Run at startup
cd /d C:\kt-rag
call venv\Scripts\activate
chainlit run ui\app.py --host 0.0.0.0 --port 8000
```

---

### 5.5 Docker Deployment (Optional — Most Portable)

#### `deploy/Dockerfile`
```dockerfile
FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["chainlit", "run", "ui/app.py", "--host", "0.0.0.0", "--port", "8000"]
```

#### `deploy/docker-compose.yml`
```yaml
version: "3.9"

services:
  ollama:
    image: ollama/ollama
    container_name: ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    restart: unless-stopped

  kt-rag:
    build:
      context: ..
      dockerfile: deploy/Dockerfile
    container_name: kt-rag
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - DOCS_DIR=/app/docs
      - VECTORSTORE_DIR=/app/vectorstore
    volumes:
      - ../docs:/app/docs
      - ../vectorstore:/app/vectorstore
    ports:
      - "8000:8000"
    depends_on:
      - ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

```bash
# Start everything with Docker
cd deploy
docker-compose up -d

# Pull models inside Ollama container (first time)
docker exec -it ollama ollama pull llama3.2
docker exec -it ollama ollama pull nomic-embed-text

# Run ingestion inside the kt-rag container
docker exec -it kt-rag python scripts/ingest.py
```

---

### 5.6 `deploy/setup_server.sh` — One-Shot Linux Setup Script

```bash
#!/bin/bash
# One-shot setup for Ubuntu/Debian office server
# Usage: bash deploy/setup_server.sh

set -e
echo "🚀 Setting up KT RAG Server..."

# System packages
sudo apt update && sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    tesseract-ocr tesseract-ocr-eng \
    curl git

# Ollama
if ! command -v ollama &> /dev/null; then
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Enable Ollama as service
sudo systemctl enable --now ollama
sleep 3

# Pull models
echo "🤖 Pulling AI models (this may take a while)..."
ollama pull llama3.2
ollama pull nomic-embed-text

# Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy your KT docs into the ./docs/ folder"
echo "  2. Run: python scripts/ingest.py"
echo "  3. Run: sudo systemctl start kt-rag"
echo "  4. Access at: http://$(hostname -I | awk '{print $1}'):8000"
```

---

## Configuration & Environment

### RAM Requirements

| Model | Min RAM | Recommended RAM |
|---|---|---|
| `llama3.2` (3B) | 4 GB | 8 GB |
| `mistral` (7B) | 8 GB | 16 GB |
| `llama3.1` (8B) | 10 GB | 16 GB |

> **Tip**: If the office machine has < 8GB RAM, use `llama3.2` (3B). If it has 16GB+, use `mistral` or `llama3.1` for better answers.

### Finding the Office Machine's LAN IP
```bash
# Linux
hostname -I

# Windows
ipconfig
# Look for "IPv4 Address" under your active adapter
```

Tell teammates: open browser → `http://<that-ip>:8000`

---

## Testing Checklist

Work through this list top to bottom before handing off:

```
[ ] Ollama is running: curl http://localhost:11434/api/tags
[ ] Models are pulled: ollama list  (should show llama3.2 and nomic-embed-text)
[ ] Docs are in ./docs/ folder (PDFs, DOCXs, images)
[ ] Ingestion runs without errors: python scripts/ingest.py
[ ] vectorstore/ folder was created and has data
[ ] CLI query works: python scripts/query.py "test question"
[ ] UI starts: chainlit run ui/app.py --host 0.0.0.0 --port 8000
[ ] UI is reachable from another machine on the same WiFi/LAN
[ ] Answer includes source document name
[ ] systemd / NSSM service auto-starts after machine reboot
[ ] Adding a new doc + re-running ingest.py works correctly
```

---

## Troubleshooting Guide

### "Connection refused" on Ollama
```bash
# Check if Ollama is running
systemctl status ollama
# Start it
sudo systemctl start ollama
# Or manually:
ollama serve
```

### Embedding errors / model not found
```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

### Tesseract not found (Windows)
```python
# Add to ingestion/image_parser.py:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### ChromaDB permission errors
```bash
chmod -R 755 ./vectorstore
```

### UI not reachable from other machines
```bash
# Check firewall — allow port 8000
sudo ufw allow 8000   # Linux
# Windows: Add inbound rule in Windows Defender Firewall for port 8000
```

### Slow responses
- Switch to a smaller model: `LLM_MODEL=llama3.2` in `.env`
- Reduce `TOP_K=3` to fetch fewer chunks
- Run on a machine with GPU for 5-10x speedup (Ollama auto-detects CUDA/Metal)

### Re-ingesting after adding new docs
```bash
# Safe to re-run — existing chunks are skipped by ID, new ones are added
python scripts/ingest.py
```

---

## README.md for Teammates

> Copy this section into a `README.md` at the project root.

```markdown
# KT Knowledge Base — How to Use

## Access
Open your browser: **http://<server-ip>:8000**

## Ask Questions Like:
- "How do I set up the local dev environment?"
- "What does the auth service do?"
- "What's the database schema for users?"
- "How do we deploy to staging?"

## Adding New Documents
1. Copy your PDF/DOCX/image into the `docs/` folder on the server
2. SSH into the server and run: `python scripts/ingest.py`
3. The new docs are immediately queryable

## Tech
- Answers come from KT documents only (no internet, no hallucinations)
- Sources are always cited in the response
- Runs 100% locally — nothing leaves the office network
```

---

*Generated for Claude Code — implement each file in order, Phase 1 through 5.*
