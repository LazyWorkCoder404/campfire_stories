import asyncio
import json

import websockets


async def main():
    async with websockets.connect("ws://localhost:8000/stats") as ws:
        for _ in range(25):  # about 5 seconds of readings
            print(json.loads(await ws.recv()))

asyncio.run(main())