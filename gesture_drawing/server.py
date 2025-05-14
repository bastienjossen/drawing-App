# server.py
import asyncio
import websockets

clients = set()

async def handler(ws, path):
    clients.add(ws)
    try:
        async for msg in ws:
            # broadcast to everyone else
            for c in clients:
                if c is not ws:
                    await c.send(msg)
    finally:
        clients.remove(ws)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 6789):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
