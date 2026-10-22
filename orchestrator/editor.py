"""A horror editor that suggests specific changes to a story."""
import json

import httpx

from orchestrator.llm import MODEL, OLLAMA_URL

EDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "replacement": {"type": "string"},
                    "note": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["dread", "pacing", "imagery", "dialogue", "cut"],
                    },
                },
                "required": ["quote", "replacement", "note", "type"],
            },
        },
    },
    "required": ["suggestions"],
}

EDITOR_PROMPT = (
    "You are a sharp, encouraging horror editor helping a writer improve their own "
    "campfire story so it is scarier and better to read aloud. Suggest 3 to 6 specific "
    "edits. For each one give: 'quote': a short passage copied EXACTLY, word for word, "
    "from the story; 'replacement': your improved version of that passage (an empty "
    "string if it should be cut); 'note': one friendly sentence to the writer explaining "
    "why; 'type': one of dread, pacing, imagery, dialogue, cut. Keep the writer's voice, "
    "characters, and plot. Never rewrite the whole story."
)


async def suggest_edits(story: str, focus: str = "") -> list[dict]:
    """Ask the editor for suggestions, optionally focused on one kind of change."""
    request = story
    if focus:
        request = f"Focus especially on this: {focus}\n\nSTORY:\n{story}"

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": EDITOR_PROMPT},
            {"role": "user", "content": request},
        ],
        "stream": False,
        "format": EDIT_SCHEMA,
        "options": {"temperature": 0.4},
    }
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

    suggestions = json.loads(response.json()["message"]["content"])["suggestions"]

    # LLMs sometimes misquote. Keep only suggestions whose quote really is in the story,
    # or the frontend would have nothing to highlight or replace.
    return [s for s in suggestions if s["quote"] and s["quote"] in story]