# KT Knowledge Base — How to Use

## Access
Open your browser: **http://&lt;server-ip&gt;:8000**

## Ask Questions Like:
- "How do I set up the local dev environment?"
- "What does the auth service do?"
- "What's the database schema for users?"
- "How do we deploy to staging?"

## Adding New Documents
1. Copy your PDF/DOCX/XLSX/XLS/TXT into the `docs/` folder on the server
2. SSH into the server and run: `python scripts/ingest.py`
3. The new docs are immediately queryable

## First-Time Setup

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed and running

### Install
```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### Pull Ollama Models (once)
```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

### Run Ingestion
```bash
python scripts/ingest.py
```

### Test a Query (CLI)
```bash
python scripts/query.py "What is the deployment process?"
```

### Launch UI
```bash
chainlit run ui/app.py --host 0.0.0.0 --port 8000
```

## Tech
- Answers come from KT documents only (no internet, no hallucinations)
- Sources are always cited in the response
- Runs 100% locally — nothing leaves the office network

## Project Structure
```
kt-rag/
├── docs/           ← PUT ALL KT DOCUMENTS HERE (pdf/, docx/, xlsx/, txt/)
├── vectorstore/    ← Auto-created ChromaDB data
├── ingestion/      ← Document parsers + chunker
├── embeddings/     ← Ollama embedding wrapper
├── vectordb/       ← ChromaDB interface
├── rag/            ← Retriever + LLM chain
├── ui/             ← Chainlit chat app
├── scripts/        ← CLI tools (ingest, query)
└── deploy/         ← Deployment configs
```
