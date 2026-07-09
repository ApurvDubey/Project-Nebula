# Nebula

Nebula is a self-hostable, open-source alternative to NotebookLM. 
It differentiates itself from standard Vector-RAG clones by using **PageIndex** (LLM-driven Tree Navigation) for deep contextual reasoning without chunking artifacts.

This project is licensed under the AGPL-3.0 License. See the [LICENSE](./LICENSE) file for more details.

## V1 Features
- PDF, DOCX, TXT, MD ingestion
- PageIndex hierarchical document tree generation
- LangGraph `plan -> fetch -> write` retrieval pipeline
- 100% offline capability via local Ollama support

## Quickstart (Docker)
```bash
docker-compose up -d --build
```
Navigate to `http://localhost:3000` to start chatting with your documents.
