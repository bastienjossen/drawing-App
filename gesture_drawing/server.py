# server.py
import asyncio
import websockets

clients: set[websockets.WebSocketServerProtocol] = set()

async def handler(ws, path):
    clients.add(ws)
    try:
        async for msg in ws:
            dead = set()
            # broadcast to everyone else, but shield exceptions
            for c in clients:
                if c is ws:
                    continue
                try:
                    await c.send(msg)
                except Exception:
                    # mark c as dead so we can remove it
                    dead.add(c)
            # clean up any dead connections
            for d in dead:
                clients.remove(d)
    finally:
        clients.remove(ws)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 6789):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
