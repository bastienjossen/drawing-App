# server.py
import asyncio
import logging
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relay")

clients: set[websockets.WebSocketServerProtocol] = set()

# Only one parameter here!
async def handler(ws):
    clients.add(ws)
    logger.info(f"Client connected: {ws.remote_address}")
    try:
        async for msg in ws:
            dead = set()
            for peer in list(clients):
                if peer is ws:
                    continue
                try:
                    await peer.send(msg)
                except Exception as e:
                    logger.warning(f"Peer {peer.remote_address} send failed: {e!r}")
                    dead.add(peer)
            for d in dead:
                clients.discard(d)
    except websockets.exceptions.ConnectionClosedOK:
        pass
    except Exception as e:
        logger.exception(f"Unexpected error in handler: {e!r}")
    finally:
        clients.discard(ws)
        logger.info(f"Client disconnected: {ws.remote_address}")

async def main():
    logger.info("Starting relay on 0.0.0.0:6789")
    async with websockets.serve(handler, "0.0.0.0", 6789):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
