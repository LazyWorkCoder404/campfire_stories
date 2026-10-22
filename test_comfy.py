import asyncio
from pathlib import Path

from orchestrator.comfy import generate_image


async def main():
    path = await generate_image(
        "An old lantern glowing on a foggy wooden dock at night",
        Path("output/test/comfy_test.png"),
    )
    print("Saved:", path)

asyncio.run(main())