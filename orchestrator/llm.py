"""Streams a story from Ollama, one chunk of text at a time."""
import json
import os

import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
# Change the model without editing code: CAMPFIRE_LLM=gemma3:27b
MODEL = os.environ.get("CAMPFIRE_LLM", "gemma3:12b")


async def stream_story(messages: list[dict]):
    """Yield text chunks from Ollama as they are generated."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "options": {"temperature": 0.9},
    }
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", OLLAMA_URL, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise RuntimeError(data["error"])
                chunk = data.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
                if data.get("done"):
                    break