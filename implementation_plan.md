# RAG System Production-Grade Optimization

## Goal
Transform the current basic RAG system into a production-quality system that can reliably answer questions from **all document types** (PDFs, images, XLSX). Currently only XLSX answers work well — PDFs and OCR-based images are not being retrieved or answered properly.

## Root Cause Analysis

| Issue | Impact | Fix |
|---|---|---|
| PDF text extraction doesn't clean noise (headers, footers, page numbers) | Chunks contain junk that dilutes semantic meaning | Add text cleaning/normalization in PDF parser |
| OCR images have no preprocessing (contrast, resize, denoise) | Poor/no text extraction from PNGs | Add PIL image preprocessing before OCR |
| Chunk size = 800 chars with 150 overlap is too aggressive for technical docs | Important context gets split across chunks, losing coherence | Increase to 1200 chars / 200 overlap |
| Only top-5 retrieval with no score threshold | Low-quality matches dilute the context sent to LLM | Add similarity score filtering + increase to top-8 |
| Basic prompt template doesn't instruct LLM to reason carefully | LLM gives up easily when context is fragmented | Add chain-of-thought reasoning prompt |
| No text normalization (whitespace, encoding) | Embedding quality degrades on noisy text | Add preprocessing in chunker |
| Ingestion has no per-document diagnostic logging | Can't tell if documents were extracted well | Add verbose ingestion stats |
| XLSX pipe-delimited format loses structure context | Key-value pairs from spreadsheets lose meaning | Add header-aware row formatting |

## Proposed Changes

### Ingestion Pipeline

---

#### [MODIFY] [pdf_parser.py](file:///c:/UOTM/RAG/KT-RAG/kt-rag/ingestion/pdf_parser.py)
- Add text cleaning: remove excessive whitespace, page numbers, repeated headers/footers
- Add fallback OCR for pages where PyMuPDF extracts no/minimal text (scanned PDFs)
- Normalize Unicode characters

#### [MODIFY] [image_parser.py](file:///c:/UOTM/RAG/KT-RAG/kt-rag/ingestion/image_parser.py)
- Add image preprocessing before OCR: convert to grayscale, increase contrast, resize for better OCR
- Add multiple OCR passes (different PSM modes) and pick best result
- Clean OCR output: remove garbage characters, fix common OCR errors

#### [MODIFY] [xlsx_parser.py](file:///c:/UOTM/RAG/KT-RAG/kt-rag/ingestion/xlsx_parser.py)
- Use header row to create "key: value" formatted text instead of pipe-delimited rows
- This makes the embedded text more semantic and searchable

#### [MODIFY] [chunker.py](file:///c:/UOTM/RAG/KT-RAG/kt-rag/ingestion/chunker.py)
- Add text preprocessing/normalization before chunking
- Prepend source document name to each chunk for better context
- Increase default chunk size and overlap via config

---

### Retrieval & RAG Pipeline

#### [MODIFY] [retriever.py](file:///c:/UOTM/RAG/KT-RAG/kt-rag/rag/retriever.py)
- Add similarity score threshold filtering (discard scores above 1.5 for cosine distance)
- Increase TOP_K to 8 for broader recall
- Add logging of retrieval scores for debugging

#### [MODIFY] [chain.py](file:///c:/UOTM/RAG/KT-RAG/kt-rag/rag/chain.py)
- Rewrite prompt template with chain-of-thought reasoning instructions
- Add structured output formatting
- Better source citation instructions

---

### Configuration

#### [MODIFY] [.env](file:///c:/UOTM/RAG/KT-RAG/kt-rag/.env)
- `CHUNK_SIZE=1200` (from 800)
- `CHUNK_OVERLAP=200` (from 150)
- `TOP_K=8` (from 5)
- Add `SCORE_THRESHOLD=1.5`

#### [MODIFY] [config.py](file:///c:/UOTM/RAG/KT-RAG/kt-rag/config.py)
- Add `SCORE_THRESHOLD` config parameter

---

### Ingestion Script

#### [MODIFY] [ingest.py](file:///c:/UOTM/RAG/KT-RAG/kt-rag/scripts/ingest.py)
- Add per-document extraction stats (chars extracted, chunks created)
- Add summary table at end showing what was ingested

## Verification Plan

### Automated Tests
1. **Re-ingest all documents**: `python scripts\ingest.py` — verify all docs produce meaningful chunks, check chunk count is significantly higher than 18
2. **Query test battery**: Run multiple queries targeting different document types:
   ```
   python scripts\query.py "What is the MFA application server setup?"
   python scripts\query.py "What is the production server setup?"
   python scripts\query.py "Explain the UOTM workflow"
   python scripts\query.py "What is the LeadProductList Manager?"
   python scripts\query.py "Explain the MiddleWare OAuth Token process"
   ```
3. Verify each query returns answers citing the correct source document(s)

### Manual Verification
- User launches `chainlit run ui\app.py --host 0.0.0.0 --port 8000` and tests queries in the chat UI
- Confirm answers come from PDFs and images, not just XLSX
