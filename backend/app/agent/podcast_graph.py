import os
import re
import json
import logging
import uuid
import edge_tts
from pydub import AudioSegment
from app.llm_provider import get_async_client
from app.agent.podcast_prompts import PODCAST_SYSTEM_PROMPT
from app.config import settings
from app.database import get_db

async def generate_podcast_audio(script_json: list[dict[str, str]], output_path: str) -> None:
    """Generate audio files using edge-tts and concatenate them using pydub."""
    
    temp_files = []
    try:
        # Generate audio for each line
        for i, line in enumerate(script_json):
            speaker = line.get("speaker", "Host 1")
            text = line.get("text", "")
            
            # Edge TTS voices (using two distinct English voices)
            voice = "en-US-ChristopherNeural" if speaker == "Host 1" else "en-US-JennyNeural"
            
            communicate = edge_tts.Communicate(text, voice)
            temp_file = f"{output_path}_temp_{i}.mp3"
            await communicate.save(temp_file)
            temp_files.append(temp_file)
            
        # Concatenate audio using pydub
        combined_audio = AudioSegment.empty()
        for temp_file in temp_files:
            audio_segment = AudioSegment.from_mp3(temp_file)
            combined_audio += audio_segment
            
        # Save final output
        combined_audio.export(output_path, format="mp3")
        
    except Exception as e:
        logging.getLogger(__name__).exception(f"Error synthesizing audio: {e}")
        raise
    finally:
        # Cleanup temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logging.getLogger(__name__).error(f"Error removing temp file {temp_file}: {e}")

async def build_podcast_script(notebook_id: str) -> list[dict[str, str]]:
    """Retrieve context and generate the podcast script."""
    # 1. Retrieve all documents for the notebook to get a sense of the context
    context_str = ""
    async with get_db() as db:
        async with db.execute("SELECT filename FROM documents WHERE notebook_id = ?", (notebook_id,)) as cursor:
            docs = await cursor.fetchall()
            if not docs:
                context_str = "This notebook is empty."
            else:
                context_str = "Notebook contains the following documents:\n" + "\n".join([d[0] for d in docs])
                
                # Fetch a short snippet from the index of the first doc if available
                async with db.execute("SELECT id FROM documents WHERE notebook_id = ? LIMIT 1", (notebook_id,)) as c2:
                    first_doc = await c2.fetchone()
                    if first_doc:
                        tree_path = os.path.join(settings.DATA_DIR, "notebooks", notebook_id, "docs", first_doc[0], "tree.json")
                        if os.path.exists(tree_path):
                            try:
                                with open(tree_path, "r", encoding="utf-8") as f:
                                    tree_data = json.load(f)
                                    context_str += "\n\nSample content:\n"
                                    for node in tree_data.get("structure", [])[:5]:
                                        context_str += node.get("summary", "") + "\n"
                            except (OSError, json.JSONDecodeError) as e:
                                logging.getLogger(__name__).warning(
                                    f"Could not read tree.json at {tree_path}: {e}"
                                )

    # 2. Call LLM to generate script
    client = get_async_client()
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": PODCAST_SYSTEM_PROMPT},
                {"role": "user", "content": f"Generate a podcast script for the following notebook context:\n\n{context_str}"}
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content or ""

        # 3. Parse JSON array
        # Clean up possible markdown code-fence wrappers, case-insensitively
        content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip(), flags=re.IGNORECASE)
        script_json = json.loads(content.strip())
        if not isinstance(script_json, list):
            raise ValueError("LLM did not return a JSON array")
            
        return script_json
        
    except Exception as e:
        logging.getLogger(__name__).exception(f"Error generating podcast script: {e}")
        return [
            {"speaker": "Host 1", "text": "Welcome to the podcast. Unfortunately, we couldn't load the notebook content today."},
            {"speaker": "Host 2", "text": "That's right. Please try again later when the system is back online."}
        ]

async def generate_podcast_task(notebook_id: str) -> None:
    """Background task to generate the podcast for a notebook."""
    try:
        uuid.UUID(notebook_id)
    except ValueError:
        logging.getLogger(__name__).error(f"Invalid notebook_id format for podcast task: {notebook_id}")
        return

    logging.info(f"Starting podcast generation for notebook {notebook_id}")

    output_dir = os.path.join(settings.DATA_DIR, "notebooks", notebook_id, "podcast")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "podcast.mp3")

    # Check if already exists (optional: we can overwrite)
    script = await build_podcast_script(notebook_id)
    await generate_podcast_audio(script, output_path)
    logging.info(f"Podcast generation completed for notebook {notebook_id}")
