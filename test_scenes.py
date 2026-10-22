import asyncio

from orchestrator.llm import stream_story
from orchestrator.prompts import build_messages
from orchestrator.scenes import split_into_scenes


async def main():
    story = ""
    async for chunk in stream_story(build_messages({"length": "short"})):
        story += chunk
    print("STORY WRITTEN. Splitting...\n")

    for number, scene in enumerate(await split_into_scenes(story), start=1):
        print(f"--- Scene {number} ---")
        print("TEXT: ", scene["text"][:100], "...")
        print("IMAGE:", scene["image_prompt"])
        print()

asyncio.run(main())