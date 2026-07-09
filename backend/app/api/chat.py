"""Chat API router.

Endpoints for managing chat sessions and messages within a notebook.
The message creation endpoint is a placeholder; the real LangGraph agent
will be wired in later.
"""

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException

import logging
from app.database import get_db
from app.models import ChatMessageCreate, ChatMessageResponse, ChatSessionResponse
from app.agent.graph import build_graph, AgentState

router = APIRouter(prefix="/api/notebooks/{notebook_id}/chat", tags=["chat"])

graph = build_graph()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(notebook_id: str) -> ChatSessionResponse:
    """Create a new chat session for a notebook.

    Args:
        notebook_id: The parent notebook UUID.

    Returns:
        The newly created chat session.
    """
    # Verify notebook exists
    async with get_db() as db:
        cursor = await db.execute(
            "SELECT id FROM notebooks WHERE id = ?", (notebook_id,)
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Notebook not found")

    session_id = str(uuid4())
    async with get_db() as db:
        await db.execute(
            "INSERT INTO chat_sessions (id, notebook_id) VALUES (?, ?)",
            (session_id, notebook_id),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT id, notebook_id, title, created_at, updated_at FROM chat_sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create session")

    return ChatSessionResponse(
        id=row["id"],
        notebook_id=row["notebook_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(notebook_id: str) -> list[ChatSessionResponse]:
    """List all chat sessions for a notebook.

    Args:
        notebook_id: The parent notebook UUID.

    Returns:
        Chat sessions ordered by most recently updated.
    """
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, notebook_id, title, created_at, updated_at
            FROM chat_sessions WHERE notebook_id = ? ORDER BY updated_at DESC
            """,
            (notebook_id,),
        )
        rows = await cursor.fetchall()
    return [
        ChatSessionResponse(
            id=row["id"],
            notebook_id=row["notebook_id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get(
    "/sessions/{session_id}/messages", response_model=list[ChatMessageResponse]
)
async def list_messages(
    notebook_id: str, session_id: str
) -> list[ChatMessageResponse]:
    """List all messages in a chat session.

    Args:
        notebook_id: The parent notebook UUID.
        session_id: The chat session UUID.

    Returns:
        Messages ordered by creation time (ascending).
    """
    async with get_db() as db:
        # Verify session belongs to notebook
        cursor = await db.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND notebook_id = ?",
            (session_id, notebook_id),
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Chat session not found")

        cursor = await db.execute(
            """
            SELECT id, role, content, citations, plan_topics, created_at
            FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()
    return [
        ChatMessageResponse(
            id=row["id"],
            role=row["role"],
            content=row["content"],
            citations=json.loads(row["citations"]),
            plan_topics=json.loads(row["plan_topics"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=201,
)
async def create_message(
    notebook_id: str, session_id: str, body: ChatMessageCreate
) -> ChatMessageResponse:
    """Send a message and get a placeholder response.

    This is a temporary stub. The real LangGraph agent (plan -> fetch -> write)
    will be wired in later.

    Args:
        notebook_id: The parent notebook UUID.
        session_id: The chat session UUID.
        body: The user message payload.

    Returns:
        A placeholder assistant response.
    """
    async with get_db() as db:
        # Verify session belongs to notebook
        cursor = await db.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND notebook_id = ?",
            (session_id, notebook_id),
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Save user message
        await db.execute(
            """
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (?, 'user', ?)
            """,
            (session_id, body.content),
        )
        await db.commit()

    initial_state: AgentState = {
        "user_query": body.content,
        "notebook_id": notebook_id,
        "session_id": session_id,
        "plan_topics": [],
        "retrieved_context": [],
        "response": "",
        "citations": [],
        "iteration_count": 0,
        "documents_relevant": ""
    }
    
    try:
        final_state = await graph.ainvoke(initial_state)
        assistant_reply = final_state.get("response", "Error generating response.")
        citations = json.dumps(final_state.get("citations", []))
        plan_topics = json.dumps(final_state.get("plan_topics", []))
    except Exception as e:
        logging.getLogger(__name__).exception(f"Graph execution failed: {e}")
        assistant_reply = f"Sorry, I encountered an error: {e}"
        citations = "[]"
        plan_topics = "[]"

    # Save assistant response in a separate transaction
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, citations, plan_topics)
            VALUES (?, 'assistant', ?, ?, ?)
            """,
            (session_id, assistant_reply, citations, plan_topics),
        )
        await db.commit()

        # Fetch the assistant message we just inserted
        cursor = await db.execute(
            """
            SELECT id, role, content, citations, plan_topics, created_at
            FROM chat_messages
            WHERE session_id = ? AND role = 'assistant'
            ORDER BY id DESC LIMIT 1
            """,
            (session_id,),
        )
        row = await cursor.fetchone()

        # Update session timestamp
        await db.execute(
            "UPDATE chat_sessions SET updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )
        await db.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="Failed to create message")

    return ChatMessageResponse(
        id=row["id"],
        role=row["role"],
        content=row["content"],
        citations=json.loads(row["citations"]),
        plan_topics=json.loads(row["plan_topics"]),
        created_at=row["created_at"],
    )
