"""Shared pytest fixtures for the Nebula backend test suite.

DATA_DIR must be pointed at a scratch directory before any `app.*` module
is imported, since `app.config.settings` and `app.database.DB_PATH` are
computed once at import time from the DATA_DIR environment variable.
"""

import os
import shutil
import tempfile
from pathlib import Path

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="nebula_test_")
os.environ["DATA_DIR"] = _TEST_DATA_DIR

import httpx
import pytest
import pytest_asyncio

from app.database import DB_PATH, init_db
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def _fresh_db():
    """Give every test a clean database and empty notebooks directory."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    notebooks_dir = os.path.join(_TEST_DATA_DIR, "notebooks")
    if os.path.exists(notebooks_dir):
        shutil.rmtree(notebooks_dir)
    await init_db()
    yield


@pytest_asyncio.fixture
async def client():
    """An httpx client wired directly to the app via ASGI, no real network."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def notebook_id(client: httpx.AsyncClient) -> str:
    """Create a notebook via the real API and return its ID."""
    resp = await client.post("/api/notebooks/", json={"name": "Test Notebook"})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
def tmp_data_dir() -> Path:
    """Path to the scratch DATA_DIR backing this test run."""
    return Path(_TEST_DATA_DIR)
