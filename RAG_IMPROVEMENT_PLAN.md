# KT RAG — Production Readiness & Improvement Plan

**Analyzed by:** AI Architecture Review
**Date:** 2026-03-12
**Codebase:** `C:\UOTM\RAG\kt-rag\`
**Status:** Functional MVP → needs targeted fixes before production use

---

## Executive Summary

The RAG is well-structured with good foundational choices (Ollama for local inference, ChromaDB for persistence, Chainlit UI, upsert-safe ingestion). However, there are **3 breaking bugs**, several **retrieval quality gaps**, and missing **production-grade features** that will affect real-world usability. This document lists every issue, its severity, and the exact fix required.

---

## Part 1 — Breaking Bugs (Must Fix First)

### BUG-01 · pdf_parser.py still imports Tesseract/Pillow
**File:** `ingestion/pdf_parser.py`
**Severity:** Critical — ingestion crashes on import if pytesseract/Pillow are not installed

**Root Cause:**
Even though Tesseract was removed from `requirements.txt`, `pdf_parser.py` still has:
```python
import pytesseract
from PIL import Image
```
And the `_ocr_page()` function calls both. Since `pytesseract` and `Pillow` are no longer in `requirements.txt`, any `import` of the module will raise `ModuleNotFoundError`.

**Fix:**
Remove the `pytesseract` and `Pillow` imports from `pdf_parser.py`. Remove the `_ocr_page()` function. Remove the OCR fallback block inside `parse_pdf()`. Pages with less than 80 chars of text should simply be skipped with a warning.

---

### BUG-02 · .xls files will crash at runtime
**File:** `ingestion/loader.py`, `ingestion/xlsx_parser.py`
**Severity:** Critical — any `.xls` file causes `InvalidFileException` and halts ingestion

**Root Cause:**
`.xls` (Excel 97-2003 binary format) is mapped to `parse_xlsx`, but `openpyxl` only reads `.xlsx` (Open XML format). It will throw `openpyxl.utils.exceptions.InvalidFileException` on any `.xls` file.

**Fix:**
Add `xlrd>=2.0.1` to `requirements.txt`. Create a separate `xls_parser.py` that uses `xlrd` to read the workbook and formats rows the same way as `xlsx_parser.py`. Map `.xls` to this new parser in `loader.py`.

---

### BUG-03 · .doc files will crash at runtime
**File:** `ingestion/loader.py`, `ingestion/docx_parser.py`
**Severity:** Critical — any `.doc` file causes a `PackageNotFoundError` and halts ingestion

**Root Cause:**
`.doc` (Word 97-2003 binary format) is mapped to `parse_docx`, but `python-docx` only reads `.docx` (Open XML format). It raises `PackageNotFoundError` on any `.doc` file.

**Fix:**
Add `docx2txt>=0.8` to `requirements.txt`. In `docx_parser.py`, detect the `.doc` extension and use `docx2txt.process()` as a fallback path for `.doc` files. Return the same `{text, metadata}` shape.

---

## Part 2 — Retrieval Quality Issues (High Impact)

### RQ-01 · No streaming — UI feels frozen for every query
**File:** `rag/chain.py`, `ui/app.py`
**Severity:** High — llama3.2 can take 15-40 seconds to generate a full answer. The user sees nothing until it's done.

**Current behavior:**
`chain.invoke(...)` blocks until the entire response is generated. The UI shows "Searching KT documents..." the whole time, then dumps the full answer at once.

**Fix:**
Replace `chain.invoke()` with `chain.stream()` and use Chainlit's streaming API (`cl.Message` with `stream=True` + `msg.stream_token()`). This lets the user read the answer as it's generated, making the app feel significantly faster.

---

### RQ-02 · No conversation history — follow-up questions fail
**File:** `rag/chain.py`, `ui/app.py`
**Severity:** High — users naturally ask follow-up questions like "Can you explain that in more detail?" which currently have no context and produce wrong answers.

**Current behavior:**
Every question is independent. The LLM has no knowledge of what was said before.

**Fix:**
Store conversation turns in Chainlit's session (`cl.user_session`). Pass the last N turns (e.g., last 3) as a `chat_history` block in the prompt template. Keep the history concise — only user question + assistant answer, not the full context.

---

### RQ-03 · DOCX parsed as a single text blob — structure lost
**File:** `ingestion/docx_parser.py`
**Severity:** High — a large DOCX (e.g., 30 pages of procedures) is returned as one flat string. The chunker then cuts it at arbitrary character positions, splitting sentences mid-way and losing which section each chunk belongs to.

**Current behavior:**
All paragraphs joined with `\n\n` → one dict returned → chunker splits at ~1200 chars regardless of document structure.

**Fix:**
Use `python-docx`'s `paragraph.style.name` to detect headings (e.g., `Heading 1`, `Heading 2`). Split the document into logical sections at heading boundaries. Return one dict per section, with the heading text included in the metadata as `section`. This means the chunker respects document structure and each chunk belongs to a named section.

---

### RQ-04 · XLSX large sheets cut mid-row by the chunker
**File:** `ingestion/xlsx_parser.py`
**Severity:** Medium-High — if a sheet has 500 rows, the chunker will split the text block at 1200 chars, potentially cutting a row's `Header: value` pairs in half.

**Current behavior:**
Entire sheet formatted as one big string → chunker splits at character boundaries.

**Fix:**
Instead of joining all rows into one string, emit rows in configurable batches (e.g., 20-30 rows per dict). This ensures the chunker never splits a single row. Batch size should be configurable. Add the row range to metadata (`rows: 1-20`).

---

### RQ-05 · LLM and VectorStore recreated on every request — slow and wasteful
**File:** `rag/chain.py`, `rag/retriever.py`, `vectordb/store.py`
**Severity:** Medium — each query creates a new `OllamaLLM` instance and a new `chromadb.PersistentClient`. This adds unnecessary overhead per query.

**Fix:**
Cache both the `OllamaLLM` instance and the vectorstore at module level (or use `@lru_cache` / Chainlit's session). Initialize once on app startup.

---

### RQ-06 · No MMR retrieval — redundant chunks hurt answer quality
**File:** `rag/retriever.py`
**Severity:** Medium — `similarity_search_with_score` can return 8 chunks that are nearly identical (e.g., 8 consecutive chunks from the same document), wasting the LLM's context window on repetition.

**Current behavior:**
`vectorstore.similarity_search_with_score(query, k=8)` — pure cosine similarity, no diversity enforcement.

**Fix:**
Replace with `vectorstore.max_marginal_relevance_search(query, k=TOP_K, fetch_k=TOP_K*3)` (MMR). This retrieves `fetch_k` candidates and selects the `k` most diverse ones, balancing relevance and coverage. Much better for multi-document KT bases.

---

### RQ-07 · Score threshold of 1.5 is not calibrated
**File:** `config.py`, `.env`, `rag/retriever.py`
**Severity:** Medium — ChromaDB returns cosine distance (0 = identical, 2 = opposite). A threshold of 1.5 means everything with any marginal relevance passes, including very poor matches.

**Context:**
For `nomic-embed-text`, well-matched KT document chunks typically score **0.1–0.4**. Scores above **0.8** are usually semantically unrelated. The threshold of 1.5 is effectively "accept everything."

**Fix:**
Calibrate the threshold. Recommended starting value: `SCORE_THRESHOLD=0.7`. The fallback logic in `retriever.py` (always returns at least one result) already prevents empty responses. Update the `.env` default.

---

## Part 3 — Robustness & Error Handling

### RB-01 · No error handling in the UI — crashes are silent
**File:** `ui/app.py`
**Severity:** Medium — if Ollama is not running, if ChromaDB is corrupted, or if retrieval returns nothing useful, the UI will show a Python traceback or freeze.

**Fix:**
Wrap the `answer(question)` call in a `try/except`. Show user-friendly messages for common failures:
- `ConnectionRefusedError` → "Ollama is not running. Please start it from the Start Menu."
- General exception → "Something went wrong. Please try again or contact the admin."

---

### RB-02 · Ingestion halts on first parse error
**File:** `ingestion/loader.py`
**Severity:** Low-Medium — the `try/except` in `load_documents` already catches errors per file, but the error message is printed with `print()` rather than being collected. If a file fails silently mid-batch, the user may not notice.

**Fix:**
Collect failed files into a list and print a summary at the end of ingestion. Already partially handled — just make the failure more prominent in the `ingest.py` summary table (add a "Failed" column).

---

### RB-03 · No Ollama connectivity check at startup
**File:** `scripts/ingest.py`, `ui/app.py`
**Severity:** Low — if Ollama isn't running, errors appear deep in the call stack with unhelpful messages.

**Fix:**
Add a pre-flight check at the start of `ingest.py` and `app.py`: make a simple HTTP GET to `{OLLAMA_BASE_URL}/api/tags`. If it fails, print a clear message and exit gracefully.

---

## Part 4 — Production Features (Missing)

### PF-01 · No way to remove a document from the vectorstore
**Severity:** Medium — once a document is ingested, it can't be removed without wiping the entire vectorstore (`rmdir /s /q vectorstore`). If a KT doc becomes outdated or is replaced, stale chunks will pollute retrieval results forever.

**Fix:**
Add a `scripts/delete_doc.py` script that takes a filename argument and deletes all ChromaDB chunks where `metadata.source == filename`. ChromaDB supports `collection.delete(where={"source": filename})`.

---

### PF-02 · No document listing / vectorstore inspection
**Severity:** Low-Medium — there is no way to see what documents are currently in the vectorstore, how many chunks each has, or when they were last ingested.

**Fix:**
Add a `scripts/list_docs.py` script that queries ChromaDB's `collection.get()`, groups by `metadata.source`, and prints a summary table (document name, file type, chunk count).

---

### PF-03 · No ingestion timestamp in metadata
**Severity:** Low — without an ingestion timestamp, there's no way to know if a document in the vectorstore is stale compared to the file on disk.

**Fix:**
Add `ingested_at: datetime.utcnow().isoformat()` to the metadata dict in `vectordb/store.py` before upserting. This enables staleness detection later.

---

## Part 5 — Code Quality Issues

### CQ-01 · DOCX heading hierarchy completely ignored
Even with the structural fix in RQ-03, heading style names like "Heading 1" / "Heading 2" / "Normal" should be preserved in metadata. This enables section-aware citation (e.g., "From: Setup.docx, Section: 'Production Deployment'").

### CQ-02 · XLSX metadata missing row range
After the batching fix in RQ-04, each batch dict should include `rows_start` and `rows_end` in metadata for precise source citation.

### CQ-03 · Chunker prefix is noisy for XLSX
`[From: Anvit's KTSheet (1).xlsx, p.1]` on every XLSX chunk is not useful — XLSX has no pages. The prefix should use the sheet name and row range for XLSX files.

### CQ-04 · `unstructured` in requirements is unused
`unstructured>=0.14.0` is listed in `requirements.txt` but never imported anywhere. It's a large, heavy package with many optional dependencies. Remove it to reduce install size and complexity.

---

## Implementation Priority Order

| # | Issue | Impact | Effort | Do First? |
|---|-------|--------|--------|-----------|
| 1 | BUG-01 — pdf_parser Tesseract import | Breaks import | 5 min | YES |
| 2 | BUG-02 — .xls crashes openpyxl | Breaks ingestion | 30 min | YES |
| 3 | BUG-03 — .doc crashes python-docx | Breaks ingestion | 30 min | YES |
| 4 | CQ-04 — remove `unstructured` | Clean deps | 2 min | YES |
| 5 | RQ-07 — score threshold calibration | Better retrieval | 2 min | YES |
| 6 | RQ-01 — streaming responses | UX | 45 min | YES |
| 7 | RQ-03 — DOCX structural parsing | Answer quality | 1 hr | YES |
| 8 | RQ-04 — XLSX row batching | Answer quality | 45 min | YES |
| 9 | RQ-06 — MMR retrieval | Answer quality | 15 min | YES |
| 10 | RQ-02 — conversation history | UX | 1 hr | High |
| 11 | RQ-05 — cache LLM/vectorstore | Performance | 30 min | High |
| 12 | RB-01 — UI error handling | Robustness | 30 min | High |
| 13 | RB-03 — Ollama pre-flight check | Robustness | 20 min | Medium |
| 14 | PF-01 — delete_doc script | Ops | 30 min | Medium |
| 15 | PF-02 — list_docs script | Ops | 20 min | Medium |
| 16 | PF-03 — ingestion timestamp | Ops | 5 min | Low |
| 17 | CQ-01/02/03 — metadata enrichment | Citations | 20 min | Low |
| 18 | RB-02 — failure summary table | Ops | 15 min | Low |

---

## What the System Gets Right (Keep As-Is)

- Upsert-based ingestion — idempotent, no duplicates
- Batched embedding (50 per batch) — memory-safe
- MD5 chunk ID hashing — stable, collision-resistant
- `temperature=0.1` — correct for factual Q&A
- Retrieval fallback (always returns ≥1 result)
- Source citation in every answer
- `chromadb.PersistentClient` with telemetry disabled
- `RecursiveCharacterTextSplitter` with good separator ordering
- `nomic-embed-text` — excellent local embedding model

---

*Ready to implement. Confirm and we will execute changes in priority order.*
