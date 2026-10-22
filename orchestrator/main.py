from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import httpx

from orchestrator.llm import stream_story
from orchestrator.prompts import build_messages

# 1. create the app
app = FastAPI(title="Campfire Stories")

SERVICES = {
    "ollama": "http://localhost:11434/api/tags",
    "comfyui": "http://127.0.0.1:8188/system_stats",
}

#The health check
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

# 3. the websocket
@app.websocket("/ws")
async def story_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Wait for the browser to ask for something
            message = await websocket.receive_json()

            if message.get("type") == "start":
                messages = build_messages(message.get("settings", {}))
                try:
                    async for chunk in stream_story(messages):
                        await websocket.send_json({"type": "token", "text": chunk})
                    await websocket.send_json({"type": "done"})
                except Exception as error:
                    await websocket.send_json({"type": "error", "message": str(error)})
    except WebSocketDisconnect:
        pass  # The browser closed the page; nothing to clean up


# 4. Serve the frontend (keep this last so it doesn't shadow the routes above)
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")