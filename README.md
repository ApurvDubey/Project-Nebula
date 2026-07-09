# Nebula

Nebula is a self-hostable, open-source alternative to NotebookLM. 
It differentiates itself from standard Vector-RAG clones by using **PageIndex** (LLM-driven Tree Navigation) for deep contextual reasoning without chunking artifacts.

This project is licensed under the AGPL-3.0 License. See the [LICENSE](./LICENSE) file for more details.

## Features

### V1 Core
- **File Ingestion**: Upload PDF, DOCX, TXT, and Markdown files.
- **PageIndex Generation**: Hierarchical document tree generation for deep understanding.
- **LangGraph Agent**: Advanced `plan -> fetch -> write` multi-step retrieval pipeline for accurate, grounded Q&A.
- **100% Offline Capability**: Connects to local Ollama out of the box for maximum privacy.

### V2 Additions
- **🌐 Live Web Scraping**: Ingest articles, blog posts, and wikis directly via URL. Features robust SSRF (Server-Side Request Forgery) protection, redirect-blocking, and DNS rebinding mitigations.
- **🧠 Interactive Knowledge Graph**: Visualize the PageIndex tree of your documents using a fully interactive React Flow graph interface.
- **Enterprise-Grade Stability**: Resilient SQLite transaction handling for concurrent LLM usage and robust exception handling.

## Quickstart (Docker)

```bash
docker-compose up -d --build
```

Navigate to `http://localhost:3000` to start chatting with your documents.

## Local Development (Without Docker)

### Backend (FastAPI)
1. `cd backend`
2. `pip install -r requirements.txt`
3. `uvicorn app.main:app --reload`
*(Server runs on port 8000)*

### Frontend (Next.js)
1. `cd frontend`
2. `npm install`
3. `npm run dev`
*(App runs on port 3000)*
