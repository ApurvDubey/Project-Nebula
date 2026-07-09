"""Notebooks API router.

CRUD endpoints for managing notebooks.
"""

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.models import NotebookCreate, NotebookResponse

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])


@router.post("/", response_model=NotebookResponse, status_code=201)
async def create_notebook(body: NotebookCreate) -> NotebookResponse:
    """Create a new notebook.

    Args:
        body: Notebook creation payload with name and optional description.

    Returns:
        The newly created notebook.
    """
    notebook_id = str(uuid4())
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO notebooks (id, name, description)
            VALUES (?, ?, ?)
            """,
            (notebook_id, body.name, body.description),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT id, name, description, index_status, created_at, updated_at FROM notebooks WHERE id = ?",
            (notebook_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create notebook")
    return NotebookResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        index_status=row["index_status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/", response_model=list[NotebookResponse])
async def list_notebooks() -> list[NotebookResponse]:
    """List all notebooks ordered by most recently updated."""
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, name, description, index_status, created_at, updated_at FROM notebooks ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
    return [
        NotebookResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            index_status=row["index_status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(notebook_id: str) -> NotebookResponse:
    """Get a single notebook by ID.

    Args:
        notebook_id: The notebook UUID.

    Returns:
        The notebook record.

    Raises:
        HTTPException: 404 if the notebook is not found.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id, name, description, index_status, created_at, updated_at FROM notebooks WHERE id = ?",
            (notebook_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return NotebookResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        index_status=row["index_status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/{notebook_id}", status_code=204)
async def delete_notebook(notebook_id: str) -> None:
    """Delete a notebook and cascade-delete its documents, sessions, and messages.

    Args:
        notebook_id: The notebook UUID.

    Raises:
        HTTPException: 404 if the notebook is not found.
    """
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM notebooks WHERE id = ?", (notebook_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Notebook not found")
        await db.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
        await db.commit()
