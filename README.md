# Nebula

Nebula is a self-hosted alternative to NotebookLM. Upload your PDFs, docs, and web pages, and ask questions grounded in what you actually gave it.

Most RAG tools chop documents into chunks and search them by vector similarity. Nebula builds a hierarchical tree of each document instead, called PageIndex, and lets an LLM agent navigate that tree the way you'd flip through a table of contents to find an answer.

Licensed under AGPL-3.0. See [LICENSE](./LICENSE).

## What it does

Upload PDF, DOCX, TXT, or Markdown files, or paste in a URL and Nebula scrapes the page for you. Each document gets turned into a PageIndex tree. Ask a question, and a LangGraph agent plans which parts of the tree to check, fetches those sections, and writes an answer with citations back to the source.

Generate a two-host podcast audio overview of your notebook context using Microsoft's free Edge TTS engine.

Point it at a local Ollama model and everything runs offline. Point it at OpenAI or another provider instead if that's what you'd rather use.

There's also a knowledge graph view: click through a document's PageIndex tree directly in a React Flow canvas.

## Under the hood

- FastAPI backend, Next.js frontend
- SQLite for storage, WAL mode, so concurrent chat sessions don't lock each other out
- URL ingestion checks the target isn't a private or internal address before fetching anything
- Tauri desktop app shell boilerplate with sidecar lifecycle management to launch/close the compiled FastAPI binary alongside the UI

## Quickstart (Docker)

```bash
docker-compose up -d --build
```

Open `http://localhost:3000` and start chatting with your documents.

## Local development (without Docker)

### Backend (FastAPI)
1. `cd backend`
2. `pip install -r requirements.txt`
3. `uvicorn app.main:app --reload`

Runs on port 8000.

### Frontend (Next.js)
1. `cd frontend`
2. `npm install`
3. `npm run dev`

Runs on port 3000.

### Desktop App (Tauri)
1. In `backend`: Build the backend binary: `python build_backend.py`
2. Move/rename the compiled binary to match Tauri's expected sidecar path: `backend/dist/nebula-backend/nebula-backend` (or `nebula-backend.exe` on Windows)
3. In `frontend`: Run `npm run tauri dev`

