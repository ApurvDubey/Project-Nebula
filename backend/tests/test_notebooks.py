"""Tests for the notebooks CRUD router."""


async def test_create_notebook_returns_the_record(client):
    resp = await client.post(
        "/api/notebooks/", json={"name": "Research", "description": "papers"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Research"
    assert body["description"] == "papers"
    assert body["index_status"] == "empty"
    assert body["id"]


async def test_create_notebook_defaults_description_to_empty_string(client):
    resp = await client.post("/api/notebooks/", json={"name": "No description"})
    assert resp.status_code == 201
    assert resp.json()["description"] == ""


async def test_create_notebook_rejects_empty_name(client):
    resp = await client.post("/api/notebooks/", json={"name": ""})
    assert resp.status_code == 422


async def test_create_notebook_rejects_missing_name(client):
    resp = await client.post("/api/notebooks/", json={})
    assert resp.status_code == 422


async def test_list_notebooks_empty_by_default(client):
    resp = await client.get("/api/notebooks/")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_notebooks_returns_created_notebooks(client, notebook_id):
    resp = await client.get("/api/notebooks/")
    assert resp.status_code == 200
    ids = [nb["id"] for nb in resp.json()]
    assert notebook_id in ids


async def test_get_notebook_returns_the_record(client, notebook_id):
    resp = await client.get(f"/api/notebooks/{notebook_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == notebook_id


async def test_get_notebook_404_when_missing(client):
    resp = await client.get("/api/notebooks/does-not-exist")
    assert resp.status_code == 404


async def test_delete_notebook_removes_it(client, notebook_id):
    resp = await client.delete(f"/api/notebooks/{notebook_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/notebooks/{notebook_id}")
    assert resp.status_code == 404


async def test_delete_notebook_404_when_missing(client):
    resp = await client.delete("/api/notebooks/does-not-exist")
    assert resp.status_code == 404
