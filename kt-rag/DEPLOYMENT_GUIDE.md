# KT RAG — Server Deployment Guide

**Last updated:** 2026-03-12
**Target:** Company local server (Linux recommended, Windows Server supported)

---

## Architecture Overview

```
  Your Office Network (LAN)
  ┌─────────────────────────────────────────────────────────┐
  │                  Company Server                         │
  │                                                         │
  │  ┌──────────────────┐    ┌───────────────────────────┐  │
  │  │  Docker:         │    │  Docker:                  │  │
  │  │  kt-rag          │───▶│  ollama                   │  │
  │  │  (Chainlit UI)   │    │  (LLM + Embeddings)       │  │
  │  │  Port 8000       │    │  Port 11434 (internal)    │  │
  │  └──────────────────┘    └───────────────────────────┘  │
  │         │                                               │
  │  ┌──────▼──────────────────────────────────────────┐   │
  │  │  Host filesystem (mounted as Docker volumes)     │   │
  │  │  /kt-rag/docs/          ← Drop new files here   │   │
  │  │  /kt-rag/vectorstore/   ← ChromaDB (auto)       │   │
  │  └─────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────┘
           │
           │ HTTP  http://server-ip:8000
           │
  ┌────────▼──────────────┐
  │  Team Members         │
  │  Any browser on LAN   │
  └───────────────────────┘
```

**Key principle:** `docs/` and `vectorstore/` are mounted as Docker volumes — they live on the host filesystem, not inside the container. This means:
- New documents can be added without rebuilding or restarting the container
- The vectorstore survives container restarts and image upgrades
- The container itself is stateless and replaceable

---

## Server Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Storage | 30 GB free | 60 GB free |
| GPU | Not required | Nvidia GPU (CUDA) for fast inference |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Network | LAN accessible | Fixed local IP or hostname |

> **GPU note:** Without a GPU, llama3.2 generates answers at ~5-15 tokens/second on a decent CPU. With an Nvidia GPU, it's ~50-100 tokens/second. For a team of 5-10 people, CPU-only is usable.

---

## Part 1 — One-Time Server Setup

### Step 1: Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in to apply group membership
```

Verify:
```bash
docker --version
docker compose version
```

### Step 2: Install Ollama on the host (recommended)

Running Ollama natively (not in Docker) gives better GPU access and simpler management:

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama
```

Pull the AI models (one-time, ~1.8 GB):
```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

Verify:
```bash
ollama list
# Should show both models
```

### Step 3: Copy the project to the server

From your Windows machine, copy the project folder to the server:
```bash
# Option A: SCP from Windows PowerShell
scp -r C:\UOTM\RAG\kt-rag user@server-ip:/opt/kt-rag

# Option B: Git clone if you push to a git repo
ssh user@server-ip
git clone <your-repo-url> /opt/kt-rag
```

### Step 4: Copy your KT documents to the server

```bash
scp -r C:\UOTM\RAG\kt-rag\docs\* user@server-ip:/opt/kt-rag/docs/
```

Or set up a shared folder (see Part 3 below for SMB setup).

---

## Part 2 — Docker Deployment

All Docker commands run from the server, inside `/opt/kt-rag/`.

### Option A: Ollama inside Docker (simpler, CPU-only servers)

The existing `deploy/docker-compose.yml` runs both Ollama and the app in Docker.

```bash
cd /opt/kt-rag

# Build the app image
docker compose -f deploy/docker-compose.yml build

# Pull Ollama models inside the Ollama container
docker compose -f deploy/docker-compose.yml run --rm ollama ollama pull llama3.2
docker compose -f deploy/docker-compose.yml run --rm ollama ollama pull nomic-embed-text

# Start everything
docker compose -f deploy/docker-compose.yml up -d
```

### Option B: Ollama on host + App in Docker (recommended for GPU servers)

Use a modified compose that points to the host Ollama instead:

```bash
cd /opt/kt-rag

# Build the app image only
docker build -f deploy/Dockerfile -t kt-rag .

# Run with Ollama pointing to the host machine
docker run -d \
  --name kt-rag \
  --restart unless-stopped \
  -p 8000:8000 \
  -e OLLAMA_BASE_URL=http://172.17.0.1:11434 \
  -e DOCS_DIR=/app/docs \
  -e VECTORSTORE_DIR=/app/vectorstore \
  -v /opt/kt-rag/docs:/app/docs \
  -v /opt/kt-rag/vectorstore:/app/vectorstore \
  kt-rag
```

> `172.17.0.1` is the default Docker bridge gateway — the host machine's IP as seen from inside a container. On some setups use `host.docker.internal` instead.

### Run Initial Ingestion

After the container is running, ingest the documents:

```bash
docker exec kt-rag python scripts/ingest.py
```

Expected output:
```
KT RAG — Document Ingestion Pipeline
Checking Ollama connectivity...
Ollama is running.
Step 1/3: Loading documents...
...
Ingestion complete! X chunks stored.
```

### Verify the UI is up

```bash
curl http://localhost:8000
# Should return HTML
```

Open from any browser on the LAN: `http://server-ip:8000`

---

## Part 3 — Adding New Documents After Deployment

This is the main workflow for ongoing use. Because `docs/` is a volume mounted from the host, you never need to rebuild or restart the container to add documents.

### Workflow

```
1. Copy new file to server → 2. Run ingestion → 3. Immediately queryable
```

### Step 1: Get the document onto the server

**Option A — SCP (from your Windows machine):**
```powershell
scp "C:\path\to\NewDocument.pdf" user@server-ip:/opt/kt-rag/docs/
```

**Option B — SMB Network Share (easiest for the team):**

Set up a Samba share on the server so team members can drag-drop files from Windows Explorer:

```bash
# Install Samba
sudo apt install samba -y

# Add this to /etc/samba/smb.conf
sudo tee -a /etc/samba/smb.conf << 'EOF'
[KT-Documents]
   path = /opt/kt-rag/docs
   browseable = yes
   read only = no
   guest ok = no
   valid users = ktadmin
EOF

# Create a Samba user
sudo smbpasswd -a ktadmin

# Restart Samba
sudo systemctl restart smbd
```

Team members on Windows can then map a network drive:
- Open File Explorer → Map Network Drive
- Folder: `\\server-ip\KT-Documents`
- They drag files in directly, no SSH needed

### Step 2: Run ingestion

```bash
docker exec kt-rag python scripts/ingest.py
```

**Or create a helper script on the server** (`/opt/kt-rag/add-docs.sh`):

```bash
#!/bin/bash
echo "Running ingestion for new documents..."
docker exec kt-rag python scripts/ingest.py
echo "Done — new documents are now queryable."
```

```bash
chmod +x /opt/kt-rag/add-docs.sh
```

Then any admin just runs:
```bash
/opt/kt-rag/add-docs.sh
```

### Remove a stale document

```bash
docker exec kt-rag python scripts/delete_doc.py "OldDocument.pdf"
# Then remove the file from docs/ as well
rm /opt/kt-rag/docs/OldDocument.pdf
```

### See what's in the vectorstore

```bash
docker exec kt-rag python scripts/list_docs.py
```

---

## Part 4 — Day-to-Day Operations

### Check container status
```bash
docker ps
# kt-rag and ollama should show as "Up"
```

### View live logs
```bash
docker logs -f kt-rag        # App logs
docker logs -f ollama        # Ollama logs
```

### Restart the app (e.g., after .env change)
```bash
docker restart kt-rag
```

### Update the app code without losing data

```bash
cd /opt/kt-rag
git pull                                          # Pull latest code
docker build -f deploy/Dockerfile -t kt-rag .    # Rebuild image
docker stop kt-rag && docker rm kt-rag

docker run -d \
  --name kt-rag \
  --restart unless-stopped \
  -p 8000:8000 \
  -e OLLAMA_BASE_URL=http://172.17.0.1:11434 \
  -e DOCS_DIR=/app/docs \
  -e VECTORSTORE_DIR=/app/vectorstore \
  -v /opt/kt-rag/docs:/app/docs \
  -v /opt/kt-rag/vectorstore:/app/vectorstore \
  kt-rag
```

The `docs/` and `vectorstore/` volumes are untouched — no re-ingestion needed.

### Change a setting (e.g., LLM model)
```bash
nano /opt/kt-rag/.env      # Edit the value
docker restart kt-rag      # Restart picks up new .env
```

### Full reset (wipe vectorstore and re-ingest everything)
```bash
docker stop kt-rag
rm -rf /opt/kt-rag/vectorstore
docker start kt-rag
docker exec kt-rag python scripts/ingest.py
```

---

## Part 5 — Auto-start on Server Reboot

Docker containers with `restart: unless-stopped` start automatically when Docker starts.
Make Docker start on boot:

```bash
sudo systemctl enable docker
sudo systemctl enable ollama    # If Ollama is on host
```

Verify after a reboot:
```bash
docker ps
# Both containers should be running automatically
```

---

## Part 6 — Security Checklist (Internal LAN)

Since this is internal-only, the requirements are lightweight:

- [ ] Server has a **fixed local IP** or a local DNS hostname (e.g., `kt-rag.company.local`)
- [ ] Port 8000 is accessible only from the office network (firewall blocks external access)
- [ ] Port 11434 (Ollama) is **not** exposed externally
- [ ] The `docs/` network share (if set up) requires authentication
- [ ] Server runs with a non-root user account

---

## What Gets Stored Where

| Data | Location | In Docker? | Backed up? |
|------|----------|------------|------------|
| KT documents | `/opt/kt-rag/docs/` | Volume (host) | Should be |
| Vector embeddings | `/opt/kt-rag/vectorstore/` | Volume (host) | Optional — can be rebuilt |
| Ollama models | Docker volume `ollama_data` | Docker volume | Not needed — re-pull if lost |
| App code | Docker image | Image layer | In git |
| Config | `/opt/kt-rag/.env` | Copied into image | Should be |

> **Backup recommendation:** Back up only `docs/` regularly. The `vectorstore/` can always be rebuilt from `docs/` by running `python scripts/ingest.py`. The Ollama models can always be re-pulled.

---

## Quick Reference Card

```bash
# First deploy
docker compose -f deploy/docker-compose.yml up -d
docker exec kt-rag python scripts/ingest.py

# Add new document
scp NewDoc.pdf user@server:/opt/kt-rag/docs/
docker exec kt-rag python scripts/ingest.py

# Remove document
docker exec kt-rag python scripts/delete_doc.py "OldDoc.pdf"

# See what's ingested
docker exec kt-rag python scripts/list_docs.py

# Restart app
docker restart kt-rag

# View logs
docker logs -f kt-rag

# Full reset
rm -rf /opt/kt-rag/vectorstore && docker exec kt-rag python scripts/ingest.py
```
