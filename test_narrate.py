import asyncio
from pathlib import Path

from orchestrator.tts import narrate


async def main():
    path = await narrate(
        "The windmill had not turned in forty years. Tonight, it turned.",
        Path("output/test/narration.wav"),
    )
    print("Saved:", path)

asyncio.run(main())