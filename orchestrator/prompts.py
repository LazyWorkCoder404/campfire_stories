"""Ask AI to write a ghost story"""

TONES = {
    "classic": "classic campfire spooky story, the kind told to friends around a fire late at night",
    "mystery": "A story centered around mystery and plot twists, but still has a ghostly element",
    "haunted_house": "a story set inside an old house where something is still living in the walls",
    "scary": "a slow-burning, deeply unsettling horror story that builds dread",
    "cozy": "a spooky-but-cozy tale, eerie and atmospheric, with a warm ending",
    "folk": "a folk-horror tale steeped in old southern American superstition and strange local customs"
}

LENGTHS= {
    "short": 250,
    "medium": 500,
    "long": 700,
}

SYSTEM_PROMPT = (
    "You are a master campfire storyteller. You write original ghost stories for adults, "
    "meant to be read aloud. Write vivid, sensory prose with a strong sense of place. "
    "Build tension steadily and end with a memorable final line. "
    "Avoid graphic gore, foul language, and sexual content. "
    "Output only the story itself: start with a title on its own line, then the story. "
    "No introductions, no notes, no markdown symbols."
)

def build_messages(settings: dict) -> list[dict]:
    """Turn the settings sent by the browser into chat messages for Ollama."""
    tone = settings.get("tone", "classic")
    tone_text = TONES.get(tone, TONES["classic"])

    length = settings.get("length", "medium")
    words = LENGTHS.get(length, LENGTHS["medium"])

    try:
        scariness = int(settings.get("scariness", 3))
    except (TypeError, ValueError):
        scariness = 3
    scariness = max(1, min(5, scariness))

    # Free-text details from the player: trim and cap the length
    details = str(settings.get("details", "")).strip()[:300]

    request = (
        f"Tell {tone_text}. "
        f"Make it about {words} words long. "
        f"On a scale of 1 (gentle) to 5 (terrifying), the scariness should be {scariness}."
    )
    if details:
        request += f" Work these details into the story: {details}"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": request},
    ]