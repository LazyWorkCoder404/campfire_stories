"""Splits a finished story into illustrated scenes."""
import json

import httpx

from orchestrator.llm import MODEL, OLLAMA_URL

# The exact shape we want back: {"scenes": [{"text": ..., "image_prompt": ...}, ...]}
SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "image_prompt": {"type": "string"},
                },
                "required": ["text", "image_prompt"],
            },
        },
    },
    "required": ["scenes"],
}

INSTRUCTIONS = (
    "Split the story you are given into 5 or 6 scenes, in order. For each scene give: "
    "'text': that part of the story, copied exactly as written; and "
    "'image_prompt': a vivid description of one illustration for that scene, covering "
    "the setting, lighting, mood, and what the characters look like. Describe only what "
    "can be seen. Never ask for words, letters, or signs in the image. Describe each "
    "character the same way in every scene so they look consistent."
)


async def split_into_scenes(story: str) -> list[dict]:
    """Ask the LLM to break a story into scenes with image prompts."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": story},
        ],
        "stream": False,          # we need the whole answer before we can use it
        "format": SCENE_SCHEMA,   # Ollama forces the reply into this shape
        "options": {"temperature": 0.3},  # low = careful and consistent
    }
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

    reply = response.json()["message"]["content"]
    return json.loads(reply)["scenes"]