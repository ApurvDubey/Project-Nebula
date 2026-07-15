"""Tests for the documents router: upload, URL ingestion, listing, deletion,
and the tree.json endpoint (including its ownership check)."""

import json
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(autouse=True)
def _skip_real_indexing(monkeypatch):
    """process_document() runs as a BackgroundTask and would otherwise try to
    call a real LLM to build a PageIndex tree. Stub it out for these tests."""
    import app.rag.engine as engine

    monkeypatch.setattr(engine, "build_document_tree", AsyncMock(return_value=None))


async def test_upload_document_success(client, notebook_id):
    files = {"file": ("notes.txt", b"hello world", "text/plain")}
    resp = await client.post(f"/api/notebooks/{notebook_id}/documents/", files=files)
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "notes.txt"
    assert body["file_type"] == "txt"
    assert body["notebook_id"] == notebook_id
    assert body["size_bytes"] == len(b"hello world")
    # Background processing (stubbed) should have marked it ready by the time
    # the ASGI request/response cycle completes.
    assert body["status"] in ("pending", "processing", "ready")


async def test_upload_document_rejects_unsupported_extension(client, notebook_id):
    files = {"file": ("virus.exe", b"MZ", "application/octet-stream")}
    resp = await client.post(f"/api/notebooks/{notebook_id}/documents/", files=files)
    assert resp.status_code == 400


async def test_upload_document_404_when_notebook_missing(client):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    resp = await client.post("/api/notebooks/does-not-exist/documents/", files=files)
    assert resp.status_code == 404


async def test_list_documents_returns_uploaded_file(client, notebook_id):
    files = {"file": ("notes.md", b"# hi", "text/markdown")}
    upload = await client.post(f"/api/notebooks/{notebook_id}/documents/", files=files)
    doc_id = upload.json()["id"]

    resp = await client.get(f"/api/notebooks/{notebook_id}/documents/")
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.json()]
    assert doc_id in ids


async def test_delete_document_removes_it(client, notebook_id):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    upload = await client.post(f"/api/notebooks/{notebook_id}/documents/", files=files)
    doc_id = upload.json()["id"]

    resp = await client.delete(f"/api/notebooks/{notebook_id}/documents/{doc_id}")
    assert resp.status_code == 204

    listing = await client.get(f"/api/notebooks/{notebook_id}/documents/")
    assert doc_id not in [d["id"] for d in listing.json()]


async def test_delete_document_404_when_missing(client, notebook_id):
    resp = await client.delete(f"/api/notebooks/{notebook_id}/documents/does-not-exist")
    assert resp.status_code == 404


async def test_get_document_tree_404_when_tree_not_built_yet(client, notebook_id):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    upload = await client.post(f"/api/notebooks/{notebook_id}/documents/", files=files)
    doc_id = upload.json()["id"]

    resp = await client.get(f"/api/notebooks/{notebook_id}/documents/{doc_id}/tree")
    assert resp.status_code == 404


async def test_get_document_tree_returns_the_tree_json(client, notebook_id, tmp_data_dir):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    upload = await client.post(f"/api/notebooks/{notebook_id}/documents/", files=files)
    doc_id = upload.json()["id"]

    tree_path = tmp_data_dir / "notebooks" / notebook_id / "docs" / doc_id / "tree.json"
    tree_path.write_text(json.dumps({"structure": [{"title": "Intro", "summary": "s"}]}))

    resp = await client.get(f"/api/notebooks/{notebook_id}/documents/{doc_id}/tree")
    assert resp.status_code == 200
    assert resp.json()["structure"][0]["title"] == "Intro"


async def test_get_document_tree_404_when_doc_belongs_to_another_notebook(
    client, notebook_id, tmp_data_dir
):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    upload = await client.post(f"/api/notebooks/{notebook_id}/documents/", files=files)
    doc_id = upload.json()["id"]

    other = await client.post("/api/notebooks/", json={"name": "Someone else's notebook"})
    other_notebook_id = other.json()["id"]

    resp = await client.get(f"/api/notebooks/{other_notebook_id}/documents/{doc_id}/tree")
    assert resp.status_code == 404


async def test_ingest_url_404_when_notebook_missing(client):
    resp = await client.post(
        "/api/notebooks/does-not-exist/documents/urls",
        json={"url": "https://example.com/article"},
    )
    assert resp.status_code == 404


async def test_ingest_url_success(client, notebook_id, monkeypatch):
    async def fake_fetch(url):
        return "My Article Title", "# My Article Title\n\nBody text."

    monkeypatch.setattr("app.api.documents.fetch_url_to_markdown", fake_fetch)

    resp = await client.post(
        f"/api/notebooks/{notebook_id}/documents/urls",
        json={"url": "https://example.com/article"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "My Article Title.md"
    assert body["file_type"] == "md"


async def test_ingest_url_400_when_fetch_fails(client, notebook_id, monkeypatch):
    async def fake_fetch(url):
        raise ValueError("Blocked private/reserved IP: 127.0.0.1")

    monkeypatch.setattr("app.api.documents.fetch_url_to_markdown", fake_fetch)

    resp = await client.post(
        f"/api/notebooks/{notebook_id}/documents/urls",
        json={"url": "http://127.0.0.1/secret"},
    )
    assert resp.status_code == 400


async def test_ingest_url_rejects_non_http_scheme(client, notebook_id):
    resp = await client.post(
        f"/api/notebooks/{notebook_id}/documents/urls",
        json={"url": "ftp://example.com/file"},
    )
    assert resp.status_code == 422
