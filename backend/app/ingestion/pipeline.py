"""Document ingestion pipeline.

Handles background processing of uploaded documents — extracting text,
building indexes, and updating document status.
"""

from datetime import datetime, timezone

from app.database import get_db


async def process_document(doc_id: str, notebook_id: str) -> None:
    """Process a newly uploaded document in the background.

    Transitions the document status through pending -> processing -> ready.

    TODO: Wire in actual content extraction (PDF, DOCX, TXT, MD).
    TODO: Build PageIndex tree from extracted content.
    TODO: Update notebook index_status accordingly.

    Args:
        doc_id: The document UUID.
        notebook_id: The parent notebook UUID.
    """
    # Mark as processing
    async with get_db() as db:
        await db.execute(
            "UPDATE documents SET status = 'processing' WHERE id = ?",
            (doc_id,),
        )
        await db.commit()

    from app.rag.engine import build_document_tree
    
    # 2. Extract content and build PageIndex tree
    try:
        await build_document_tree(notebook_id, doc_id)
        # TODO: Merge into notebook-level index
    except Exception as e:
        # Mark as failed
        async with get_db() as db:
            await db.execute(
                "UPDATE documents SET status = 'failed', error_message = ? WHERE id = ?",
                (str(e), doc_id),
            )
            await db.commit()
        return

    # Mark as ready
    now = datetime.now(timezone.utc).isoformat()
    async with get_db() as db:
        await db.execute(
            "UPDATE documents SET status = 'ready', processed_at = ? WHERE id = ?",
            (now, doc_id),
        )
        await db.commit()
