import asyncio
import uuid
from pathlib import Path
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import httpx

from orchestrator.comfy import generate_image
from orchestrator.llm import stream_story
from orchestrator.prompts import build_messages
from orchestrator.scenes import split_into_scenes
from orchestrator.telemetry import read_stats
from orchestrator.tts import narrate
from orchestrator.extract import extract_text
from orchestrator.editor import suggest_edits

PROJECT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 1. create the app
app = FastAPI(title="Campfire Stories")

SERVICES = {
    "ollama": "http://localhost:11434/api/tags",
    "comfyui": "http://127.0.0.1:8188/system_stats",
}


# 2. the health check
@app.get("/health")
async def health():
    results = {}
    async with httpx.AsyncClient(timeout=3) as client:
        for name, url in SERVICES.items():
            try:
                results[name] = (await client.get(url)).status_code == 200
            except httpx.HTTPError:
                results[name] = False
    return results

# Upload a story file and get its text back
@app.post("/upload")
async def upload(file: UploadFile):
    data = await file.read()
    if len(data) > 5_000_000:
        raise HTTPException(status_code=413, detail="That file is too big (5 MB max)")
    try:
        return {"text": extract_text(file.filename or "", data)}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(status_code=400, detail="Sorry, that file couldn't be read")

class EditRequest(BaseModel):
    story: str
    focus: str = ""

# Ask the horror editor for suggestions
@app.post("/edit")
async def edit(request: EditRequest):
    story = request.story[:12000]
    focus = request.focus[:200]
    return {"suggestions": await suggest_edits(story, focus)}

# 3. the story pipeline (NEW): write, plan the scenes, illustrate
# 3a. Writing: stream the story, then stop and let the visitor decide
async def write_story(websocket: WebSocket, settings: dict):
    await websocket.send_json({"type": "stage", "stage": "The storyteller leans in..."})
    async for chunk in stream_story(build_messages(settings)):
        await websocket.send_json({"type": "token", "text": chunk})
    await websocket.send_json({"type": "written"})


# 3b. Bringing it to life: scenes, pictures, and narration
async def bring_to_life(websocket: WebSocket, story: str):
    story_id = uuid.uuid4().hex[:8]  # a short random name for this story's folder

    await websocket.send_json({"type": "stage", "stage": "Picturing the scenes..."})
    scenes = await split_into_scenes(story)

    folder = OUTPUT_DIR / story_id
    for number, scene in enumerate(scenes, start=1):
        await websocket.send_json({
            "type": "stage",
            "stage": f"Bringing scene {number} of {len(scenes)} to life...",
        })
        await asyncio.gather(
            generate_image(scene["image_prompt"], folder / f"scene_{number}.png"),
            narrate(scene["text"], folder / f"scene_{number}.wav"),
        )
        await websocket.send_json({
            "type": "scene",
            "scene": number,
            "total": len(scenes),
            "image": f"/output/{story_id}/scene_{number}.png",
            "audio": f"/output/{story_id}/scene_{number}.wav",
            "text": scene["text"],
        })

    await websocket.send_json({"type": "done"})


# 4. the story websocket: two kinds of request
@app.websocket("/ws")
async def story_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_json()
            try:
                if message.get("type") == "start":
                    await write_story(websocket, message.get("settings", {}))
                elif message.get("type") == "animate":
                    story = str(message.get("story", ""))[:20000]  # cap the length
                    await bring_to_life(websocket, story)
            except WebSocketDisconnect:
                raise  # the page closed; let the outer handler deal with it
            except Exception as error:
                await websocket.send_json({"type": "error", "message": str(error)})
    except WebSocketDisconnect:
        pass  # The browser closed the page; nothing to clean up

# 5. the live GPU stats
@app.websocket("/stats")
async def stats_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(read_stats())
            await asyncio.sleep(0.2)  # five readings per second
    except Exception:
        pass  # The page was closed; stop sending


# 6. Serve generated images (NEW), then the frontend (keep the frontend last)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")