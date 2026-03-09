#!/bin/bash
# One-shot setup for Ubuntu/Debian office server
# Usage: bash deploy/setup_server.sh

set -e
echo "Setting up KT RAG Server..."

# System packages
sudo apt update && sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    tesseract-ocr tesseract-ocr-eng \
    curl git

# Ollama
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Enable Ollama as service
sudo systemctl enable --now ollama
sleep 3

# Pull models
echo "Pulling AI models (this may take a while)..."
ollama pull llama3.2
ollama pull nomic-embed-text

# Python environment
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy your KT docs into the ./docs/ folder"
echo "  2. Run: python scripts/ingest.py"
echo "  3. Run: sudo systemctl start kt-rag"
echo "  4. Access at: http://$(hostname -I | awk '{print $1}'):8000"
