"""RAG engine using PageIndex tree navigation.

This module will contain the core retrieval logic that navigates the
PageIndex tree structure instead of using vector similarity search.
"""

import json
import asyncio
from pathlib import Path
from typing import Any

import logging
from app.database import get_db
from app.config import settings
from app.pageindex_engine.page_index import page_index_main
from app.pageindex_engine.page_index_md import md_to_tree
from app.pageindex_engine.utils import ConfigLoader


async def build_document_tree(notebook_id: str, document_id: str) -> None:
    """Build a PageIndex tree for a single document and save it to disk.

    Args:
        notebook_id: The notebook UUID.
        document_id: The document UUID.
    """
    async with get_db() as db:
        async with db.execute(
            "SELECT storage_path, file_type FROM documents WHERE id = ?", (document_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise ValueError(f"Document {document_id} not found")
            storage_path, file_type = row

    opt = ConfigLoader().load()
    opt.model = settings.LLM_MODEL
    
    # Pre-conversion logic for docx/txt would normally happen here or in ingestion pipeline
    if file_type == 'pdf':
        tree = await asyncio.to_thread(page_index_main, storage_path, opt)
    elif file_type in ['md', 'txt', 'docx']:
        # Assuming extract.py converts txt/docx to md first and updates storage_path to .md
        tree = await md_to_tree(storage_path, model=settings.LLM_MODEL)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    tree_path = Path(storage_path).parent / "tree.json"
    with open(tree_path, "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)


async def retrieve_from_notebook(
    notebook_id: str, topics: list[str]
) -> list[dict[str, Any]]:
    """Retrieve relevant context from a notebook's PageIndex tree.
    
    Args:
        notebook_id: The notebook UUID.
        topics: List of search topics extracted by the planning step.

    Returns:
        List of context dicts with keys: content, source_filename, score.
    """
    import re
    import math
    from app.pageindex_engine.utils import get_leaf_nodes
    
    def tokenize(text):
        return set(re.findall(r'\w+', str(text).lower()))
        
    query_tokens = set()
    for topic in topics:
        if topic and topic.upper() != "NONE":
            query_tokens.update(tokenize(topic))
            
    if not query_tokens:
        return []
        
    results = []
    
    async with get_db() as db:
        async with db.execute(
            "SELECT storage_path, filename FROM documents WHERE notebook_id = ? AND status = 'ready'",
            (notebook_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            
    for storage_path, filename in rows:
        tree_path = Path(storage_path).parent / "tree.json"
        if not tree_path.exists():
            continue
            
        try:
            with open(tree_path, "r", encoding="utf-8") as f:
                tree = json.load(f)
        except Exception as e:
            logging.getLogger(__name__).exception(f"Failed to load tree.json for {filename}: {e}")
            continue
            
        leaf_nodes = get_leaf_nodes(tree) or []
        
        for node in leaf_nodes:
            text = node.get('text', '')
            summary = node.get('summary', '')
            title = node.get('title', '')
            
            # Simple TF-like overlap scoring
            node_tokens = tokenize(text) | tokenize(summary) | tokenize(title)
            overlap = len(query_tokens.intersection(node_tokens))
            
            if overlap > 0:
                results.append({
                    "content": f"Title: {title}\nSummary: {summary}\n\n{text}",
                    "source_filename": filename,
                    "section_path": title,
                    "score": overlap / math.sqrt(max(len(node_tokens), 1))
                })
                
    # Sort and return top 5
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:5]
