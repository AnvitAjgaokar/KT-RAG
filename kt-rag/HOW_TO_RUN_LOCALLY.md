# How to Run KT RAG Locally

**Last updated:** 2026-03-12
**Project path:** `C:\UOTM\RAG\kt-rag\`

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11 or 3.12 | https://python.org/downloads |
| Ollama | Latest | https://ollama.com/download/windows |

> **Note:** Tesseract OCR is NOT required. The system handles PDF, DOCX, DOC, XLSX, XLS, and TXT files natively.

---

## Step 1 — Install Python

1. Download Python 3.11 or 3.12 from https://python.org/downloads
2. Run the installer — **check "Add python.exe to PATH"** before clicking Install
3. Verify in a new PowerShell window:
   ```
   python --version
   ```

---

## Step 2 — Install Ollama

1. Download from https://ollama.com/download/windows and install
2. It runs as a background service automatically after install
3. Verify:
   ```
   ollama --version
   ```

---

## Step 3 — Pull the AI Models

Run these in PowerShell (one-time download — ~1.5 GB + ~300 MB):

```powershell
ollama pull llama3.2
ollama pull nomic-embed-text
```

Confirm both are ready:
```powershell
ollama list
```

---

## Step 4 — Set Up Python Virtual Environment

Open PowerShell and navigate to the project:

```powershell
cd C:\UOTM\RAG\kt-rag
python -m venv venv
venv\Scripts\activate
```

Your prompt should now show `(venv)`.

---

## Step 5 — Install Python Dependencies

```powershell
pip install -r requirements.txt
```

This installs: LangChain, ChromaDB, Chainlit, PyMuPDF, openpyxl, xlrd, docx2txt, rich, etc.

> **After any future `requirements.txt` change**, re-run this command with the venv active.

---

## Step 6 — Add Your KT Documents

Drop your files into the `docs\` folder. Supported formats:

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text-based PDFs only; scanned/blank pages are skipped |
| Word (new) | `.docx` | Split at headings for better retrieval |
| Word (legacy) | `.doc` | Full text extracted via docx2txt |
| Excel (new) | `.xlsx` | Rows extracted in batches per sheet |
| Excel (legacy) | `.xls` | Same as xlsx — rows extracted in batches |
| Plain text | `.txt` | UTF-8 encoded |

You can organise them in subfolders — the ingestion script walks the entire `docs\` tree.

---

## Step 7 — Run Document Ingestion

> **If re-ingesting after code changes, wipe the old vectorstore first:**
> ```powershell
> rmdir /s /q vectorstore
> ```

Then run:
```powershell
python scripts\ingest.py
```

Expected output:
```
KT RAG — Document Ingestion Pipeline

Docs directory : ./docs
Vector store   : ./vectorstore
Embed model    : nomic-embed-text

Checking Ollama connectivity...
Ollama is running.

Step 1/3: Loading documents...
  Loading: LeadProductList Manager.pdf
  Loading: MFA_Application_Server_APP.pdf
  Loading: Anvit's KTSheet (1).xlsx
  ...
✅ Loaded X document sections

Step 2/3: Chunking documents...
✅ Created X chunks from X document sections

Step 3/3: Embedding & storing...
📥 Embedding X chunks into ChromaDB...
  ✅ Upserted batch 1 (50/X)
  ...
✅ Stored X chunks in vectorstore

┌─────────────────────────────────────────────────────────┐
│                   Ingestion Summary                     │
├─────────────────────┬───────┬──────────┬───────┬────────┤
│ Document            │ Type  │ Sections │ Chunks│ Chars  │
└─────────────────────┴───────┴──────────┴───────┴────────┘

Ingestion complete! X chunks stored.
```

The first run embeds everything and may take a few minutes. The `vectorstore\` folder is created automatically. **Re-runs are safe** — existing chunks are updated, not duplicated.

---

## Step 8 — Test with a CLI Query

Before launching the UI, verify the pipeline works:

```powershell
python scripts\query.py "What is the MFA application server setup?"
```

You should see an answer with source citations. If you get a good answer, the pipeline is working.

---

## Step 9 — Launch the Chat UI

```powershell
chainlit run ui\app.py --host 0.0.0.0 --port 8000
```

Then open your browser:
- **Local:** http://localhost:8000
- **From another device on the same network:** http://YOUR-PC-IP:8000

To find your PC's IP:
```powershell
ipconfig
```
Look for the `IPv4 Address` under your active network adapter.

---

## Day-to-Day Usage

### Add a new document
```powershell
# 1. Copy the file into docs\
# 2. Run ingestion (safe to re-run — no duplicates)
python scripts\ingest.py
```

### See what's in the vectorstore
```powershell
python scripts\list_docs.py
```

Output shows each document, its type, chunk count, and when it was last ingested.

### Remove a stale document
```powershell
python scripts\delete_doc.py "OldDocument.pdf"
```

This removes only that document's chunks from the vectorstore without affecting others.

---

## Configuration

All settings live in `.env` at the project root. Edit them with any text editor:

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_MODEL` | `llama3.2` | Ollama model for generating answers |
| `EMBED_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API address |
| `CHUNK_SIZE` | `1200` | Max characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |
| `TOP_K` | `8` | Number of chunks retrieved per query |
| `SCORE_THRESHOLD` | `0.7` | Relevance cutoff (lower = stricter) |
| `UI_PORT` | `8000` | Chainlit UI port |

After changing `.env`, restart the UI (`Ctrl+C` then relaunch) for changes to take effect.
After changing `CHUNK_SIZE`, `CHUNK_OVERLAP`, or `EMBED_MODEL`, wipe and rebuild the vectorstore.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ollama: command not found` | Restart PowerShell after Ollama install |
| `Cannot reach Ollama at http://localhost:11434` | Open Ollama from the Start Menu |
| `ModuleNotFoundError` | Make sure `(venv)` is active, re-run `pip install -r requirements.txt` |
| `Slow ingestion` | Normal on first run — embeddings take time. Re-runs are fast (upsert). |
| `Answers are wrong or unrelated` | Lower `SCORE_THRESHOLD` in `.env` (e.g., `0.5`), then test again |
| `Scanned PDF pages skipped` | Expected — scanned pages have no extractable text and are skipped |
| `.xls file parse error` | Make sure `xlrd` is installed: `pip install xlrd>=2.0.1` |
| `.doc file parse error` | Make sure `docx2txt` is installed: `pip install docx2txt>=0.8` |
| Port 8000 already in use | Change `UI_PORT` in `.env` or kill the existing process |
| Want to reset everything | `rmdir /s /q vectorstore` then re-run `python scripts\ingest.py` |
