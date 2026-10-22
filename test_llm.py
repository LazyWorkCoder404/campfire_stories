import asyncio

from orchestrator.llm import stream_story
from orchestrator.prompts import build_messages


async def main():
    messages = build_messages({"tone": "classic", "length": "short", "scariness": 3})
    async for chunk in stream_story(messages):
        print(chunk, end="", flush=True)
    print()

asyncio.run(main())