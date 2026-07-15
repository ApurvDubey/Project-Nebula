import os
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from app.agent.podcast_graph import generate_podcast_task
from app.config import settings

router = APIRouter(prefix="/api/notebooks/{notebook_id}/podcast", tags=["podcast"])

def _validate_uuid(notebook_id: str):
    try:
        uuid.UUID(notebook_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notebook ID format")

@router.post("/")
async def generate_podcast(notebook_id: str, background_tasks: BackgroundTasks):
    """Trigger podcast generation in the background."""
    _validate_uuid(notebook_id)
    background_tasks.add_task(generate_podcast_task, notebook_id)
    return {"status": "processing"}

@router.get("/")
async def get_podcast(notebook_id: str):
    """Get the generated podcast audio file if ready."""
    _validate_uuid(notebook_id)
    output_path = os.path.join(settings.DATA_DIR, "notebooks", notebook_id, "podcast", "podcast.mp3")
    
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Podcast not found or still generating")
        
    return FileResponse(output_path, media_type="audio/mpeg", filename=f"notebook_{notebook_id}_podcast.mp3")
