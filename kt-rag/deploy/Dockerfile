FROM python:3.12-slim

# libgl1 is required by PyMuPDF (PDF parsing)
RUN apt-get update && apt-get install -y \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (docs/ and vectorstore/ are mounted as volumes — not copied)
COPY config.py .
COPY .env .
COPY ingestion/ ingestion/
COPY embeddings/ embeddings/
COPY vectordb/ vectordb/
COPY rag/ rag/
COPY ui/ ui/
COPY scripts/ scripts/

EXPOSE 8000

CMD ["chainlit", "run", "ui/app.py", "--host", "0.0.0.0", "--port", "8000"]
