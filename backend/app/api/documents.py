"""Documents API router.

Endpoints for uploading, listing, and deleting documents within a notebook.
"""

import hashlib
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.database import get_db
from app.ingestion.pipeline import process_document
from app.ingestion.web import fetch_url_to_markdown
from app.models import DocumentResponse, UrlIngestRequest

router = APIRouter(
    prefix="/api/notebooks/{notebook_id}/documents", tags=["documents"]
)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}


def _get_extension(filename: str) -> str:
    """Extract and validate file extension from a filename.

    Args:
        filename: The original filename.

    Returns:
        The lowercase extension without the leading dot.

    Raises:
        HTTPException: 400 if the extension is not allowed.
    """
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


async def _create_document_record(
    notebook_id: str,
    doc_id: str,
    filename: str,
    ext: str,
    content_bytes: bytes,
    background_tasks: BackgroundTasks,
) -> DocumentResponse:
    content_hash = hashlib.sha256(content_bytes).hexdigest()
    size_bytes = len(content_bytes)

    # Save to disk
    doc_dir = Path(settings.DATA_DIR) / "notebooks" / notebook_id / "docs" / doc_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    storage_path = doc_dir / f"source.{ext}"
    storage_path.write_bytes(content_bytes)

    # Insert DB record
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO documents
                (id, notebook_id, filename, file_type, storage_path, size_bytes, content_hash, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (doc_id, notebook_id, filename, ext, str(storage_path), size_bytes, content_hash),
        )
        await db.commit()
        cursor = await db.execute(
            """
            SELECT id, notebook_id, filename, file_type, status, size_bytes, created_at, processed_at
            FROM documents WHERE id = ?
            """,
            (doc_id,),
        )
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create document record")

    # Queue background processing
    background_tasks.add_task(process_document, doc_id, notebook_id)

    return DocumentResponse(
        id=row["id"],
        notebook_id=row["notebook_id"],
        filename=row["filename"],
        file_type=row["file_type"],
        status=row["status"],
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
        processed_at=row["processed_at"],
    )


@router.post("/", response_model=DocumentResponse, status_code=201)
async def upload_document(
    notebook_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks,
) -> DocumentResponse:
    """Upload a document to a notebook.

    Validates the file extension, saves the file to disk, creates a DB record
    with status 'pending', and kicks off background processing.

    Args:
        notebook_id: The parent notebook UUID.
        file: The uploaded file.
        background_tasks: FastAPI background task manager.

    Returns:
        The newly created document record.
    """
    # Verify notebook exists
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM notebooks WHERE id = ?", (notebook_id,)
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Notebook not found")

    filename = file.filename or "unnamed"
    ext = _get_extension(filename)
    doc_id = str(uuid4())

    # Read file content
    content_bytes = await file.read()
    
    return await _create_document_record(notebook_id, doc_id, filename, ext, content_bytes, background_tasks)


@router.post("/urls", response_model=DocumentResponse, status_code=201)
async def ingest_url(
    notebook_id: str,
    request: UrlIngestRequest,
    background_tasks: BackgroundTasks,
) -> DocumentResponse:
    """Ingest a URL by scraping its HTML to markdown."""
    # Verify notebook exists
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM notebooks WHERE id = ?", (notebook_id,)
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Notebook not found")

    doc_id = str(uuid4())
    
    try:
        title, md_content = await fetch_url_to_markdown(request.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

    filename = title + ".md"
    ext = "md"
    content_bytes = md_content.encode("utf-8")
    
    return await _create_document_record(notebook_id, doc_id, filename, ext, content_bytes, background_tasks)


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(notebook_id: str) -> list[DocumentResponse]:
    """List all documents in a notebook.

    Args:
        notebook_id: The parent notebook UUID.

    Returns:
        List of document records ordered by creation time.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, notebook_id, filename, file_type, status, size_bytes, created_at, processed_at
            FROM documents WHERE notebook_id = ? ORDER BY created_at ASC
            """,
            (notebook_id,),
        )
        rows = await cursor.fetchall()
    return [
        DocumentResponse(
            id=row["id"],
            notebook_id=row["notebook_id"],
            filename=row["filename"],
            file_type=row["file_type"],
            status=row["status"],
            size_bytes=row["size_bytes"],
            created_at=row["created_at"],
            processed_at=row["processed_at"],
        )
        for row in rows
    ]


@router.delete("/{doc_id}", status_code=204)
async def delete_document(notebook_id: str, doc_id: str) -> None:
    """Delete a document and its files from disk.

    Args:
        notebook_id: The parent notebook UUID.
        doc_id: The document UUID.

    Raises:
        HTTPException: 404 if the document is not found.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, storage_path FROM documents WHERE id = ? AND notebook_id = ?",
            (doc_id, notebook_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Document not found")

        # Remove from DB
        await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await db.commit()

    # Remove files from disk
    doc_dir = Path(settings.DATA_DIR) / "notebooks" / notebook_id / "docs" / doc_id
    if doc_dir.exists():
        shutil.rmtree(doc_dir)


@router.get("/{doc_id}/tree")
async def get_document_tree(notebook_id: str, doc_id: str) -> FileResponse:
    """Retrieve the generated tree.json for a document to visualize in React Flow."""
    # Verify document ownership
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM documents WHERE id = ? AND notebook_id = ?",
            (doc_id, notebook_id),
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Document not found or belongs to another notebook")

    tree_path = Path(settings.DATA_DIR) / "notebooks" / notebook_id / "docs" / doc_id / "tree.json"
    
    if not tree_path.exists():
        raise HTTPException(status_code=404, detail="Tree JSON not found for this document")
        
    return FileResponse(tree_path, media_type="application/json")
