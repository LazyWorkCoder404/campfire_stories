import asyncio
import json

import websockets


async def main():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        await ws.send(json.dumps({"type": "start", "settings": {"length": "short"}}))
        while True:
            message = json.loads(await ws.recv())
            if message["type"] == "token":
                print(message["text"], end="", flush=True)
            else:
                print("\n\n[" + message["type"] + "]", message.get("message", ""))
                break

asyncio.run(main())