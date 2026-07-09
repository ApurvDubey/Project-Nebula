"""Async SQLite database layer using aiosqlite.

Provides init_db() for schema creation and get_db() context manager
for obtaining database connections.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

from app.config import settings

DB_PATH: str = os.path.join(settings.DATA_DIR, "nebula.db")

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS notebooks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    index_status TEXT DEFAULT 'empty' CHECK(index_status IN ('empty','building','ready','stale','failed')),
    index_error TEXT DEFAULT '',
    content_hash TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK(file_type IN ('pdf','docx','txt','md')),
    storage_path TEXT NOT NULL,
    size_bytes INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending','processing','ready','failed')),
    error_message TEXT DEFAULT '',
    page_count INTEGER,
    word_count INTEGER,
    content_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    processed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_documents_notebook ON documents(notebook_id, created_at ASC);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New chat',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content TEXT NOT NULL,
    citations TEXT DEFAULT '[]',
    plan_topics TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now'))
);
"""


async def init_db() -> None:
    """Initialize the database: create data directory and all tables.

    Enables WAL mode and foreign keys for performance and integrity.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA_SQL)
        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that yields an aiosqlite connection.

    Usage::

        async with get_db() as db:
            await db.execute(...)
    """
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
    finally:
        await db.close()
