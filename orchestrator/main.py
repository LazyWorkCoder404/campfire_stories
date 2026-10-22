import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import httpx

from orchestrator.comfy import generate_image
from orchestrator.llm import stream_story
from orchestrator.prompts import build_messages
from orchestrator.scenes import split_into_scenes
from orchestrator.telemetry import read_stats

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


# 3. the story pipeline (NEW): write, plan the scenes, illustrate
async def tell_story(websocket: WebSocket, settings: dict):
    story_id = uuid.uuid4().hex[:8]  # a short random name for this story's folder

    # Writing: stream it to the browser, and keep the full text for later
    await websocket.send_json({"type": "stage", "stage": "The storyteller leans in..."})
    story = ""
    async for chunk in stream_story(build_messages(settings)):
        story += chunk
        await websocket.send_json({"type": "token", "text": chunk})

    # Planning: split the story into scenes with image prompts
    await websocket.send_json({"type": "stage", "stage": "Picturing the scenes..."})
    scenes = await split_into_scenes(story)

    # Illustrating: one image per scene, sent as soon as each is ready
    for number, scene in enumerate(scenes, start=1):
        await websocket.send_json({
            "type": "stage",
            "stage": f"Painting scene {number} of {len(scenes)}...",
        })
        filename = f"scene_{number}.png"
        await generate_image(scene["image_prompt"], OUTPUT_DIR / story_id / filename)
        await websocket.send_json({
            "type": "image",
            "scene": number,
            "url": f"/output/{story_id}/{filename}",
            "caption": scene["text"],
        })

    await websocket.send_json({"type": "done"})


# 4. the story websocket (now hands the work to tell_story)
@app.websocket("/ws")
async def story_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Wait for the browser to ask for something
            message = await websocket.receive_json()

            if message.get("type") == "start":
                try:
                    await tell_story(websocket, message.get("settings", {}))
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