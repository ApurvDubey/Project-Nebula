import asyncio
import httpx
from app.main import app
from app.database import init_db

async def create_notebook_and_session(client: httpx.AsyncClient) -> tuple[str, str]:
    resp = await client.post("/api/notebooks/", json={"name": "test_notebook", "description": ""})
    notebook_id = resp.json()["id"]
    
    resp = await client.post(f"/api/notebooks/{notebook_id}/chat/sessions")
    session_id = resp.json()["id"]
    return notebook_id, session_id

async def send_message(client: httpx.AsyncClient, notebook_id: str, session_id: str, msg: str):
    print(f"Sending message: {msg}")
    resp = await client.post(
        f"/api/notebooks/{notebook_id}/chat/sessions/{session_id}/messages",
        json={"content": msg}
    )
    print(f"Received response for {msg}: {resp.status_code}")
    return resp.json()

async def test_concurrency():
    await init_db()
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            notebook_id, session_id = await create_notebook_and_session(client)
        except Exception as e:
            print(f"Failed to create notebook/session: {e}")
            return
            
        print(f"Created Notebook: {notebook_id}, Session: {session_id}")
        
        # Send two concurrent messages
        task1 = asyncio.create_task(send_message(client, notebook_id, session_id, "Message A"))
        task2 = asyncio.create_task(send_message(client, notebook_id, session_id, "Message B"))
        
        await asyncio.gather(task1, task2)
        
        # Verify messages
        resp = await client.get(f"/api/notebooks/{notebook_id}/chat/sessions/{session_id}/messages")
        messages = resp.json()
        print(f"Total messages in session: {len(messages)}")
        for i, m in enumerate(messages):
            print(f"  {i}: {m['role']} - {m['content']}")

if __name__ == "__main__":
    asyncio.run(test_concurrency())
