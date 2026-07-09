"""Pydantic models for request/response validation."""

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


# ── Notebooks ────────────────────────────────────────────────────────

class NotebookCreate(BaseModel):
    """Schema for creating a new notebook."""

    name: str = Field(..., min_length=1, max_length=255, description="Notebook name")
    description: str = Field(default="", max_length=2000, description="Optional description")


class NotebookResponse(BaseModel):
    """Schema for notebook API responses."""

    id: str
    name: str
    description: str
    index_status: str
    created_at: str
    updated_at: str


# ── Documents ────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    """Schema for document API responses."""

    id: str
    notebook_id: str
    filename: str
    file_type: str
    status: str
    size_bytes: int
    created_at: str
    processed_at: Optional[str] = None


class UrlIngestRequest(BaseModel):
    """Schema for ingesting a URL as a document."""

    url: HttpUrl = Field(..., description="The URL to scrape and ingest")


# ── Chat ─────────────────────────────────────────────────────────────

class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message."""

    content: str = Field(..., min_length=1, description="Message content")


class ChatMessageResponse(BaseModel):
    """Schema for chat message API responses."""

    id: int
    role: str
    content: str
    citations: List[str] = Field(default_factory=list)
    plan_topics: List[str] = Field(default_factory=list)
    created_at: str


class ChatSessionResponse(BaseModel):
    """Schema for chat session API responses."""

    id: str
    notebook_id: str
    title: str
    created_at: str
    updated_at: str
