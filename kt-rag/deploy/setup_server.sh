#!/bin/bash
# One-shot setup for Ubuntu/Debian office server (bare-metal, no Docker)
# Usage: bash deploy/setup_server.sh

set -e
echo "Setting up KT RAG Server..."

# System packages
sudo apt update && sudo apt install -y \
    python3.12 python3.12-venv python3-pip \
    curl git libgl1

# Docker (if not already installed)
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to log out and back in."
fi

# Ollama
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Enable Ollama as a system service
sudo systemctl enable --now ollama
sleep 5

# Pull AI models (one-time download ~1.8 GB)
echo "Pulling AI models — this may take several minutes..."
ollama pull llama3.2
ollama pull nomic-embed-text

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  Option A — Docker Compose (recommended):"
echo "    cd $(pwd)/.."
echo "    docker compose -f deploy/docker-compose.yml up -d"
echo ""
echo "  Option B — Bare metal (venv):"
echo "    python3.12 -m venv venv"
echo "    source venv/bin/activate"
echo "    pip install -r requirements.txt"
echo "    python scripts/ingest.py"
echo "    chainlit run ui/app.py --host 0.0.0.0 --port 8000"
echo ""
echo "  Access at: http://$(hostname -I | awk '{print $1}'):8000"
