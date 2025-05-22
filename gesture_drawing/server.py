# server.py
import asyncio
import logging
import websockets
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("relay")

clients: dict[str, websockets.WebSocketServerProtocol] = {}   # id → ws

# Only one parameter here!
async def handler(ws):
    my_id: str | None = None
    try:
        async for msg in ws:
            data = json.loads(msg)

            # ① first message from each client must be {"type":"hello","id":…}
            if data.get("type") == "hello":
                my_id = data["id"]
                clients[my_id] = ws
                logger.info(f"Registered client {my_id} @ {ws.remote_address}")
                continue

            # ② directed message?
            target = data.pop("to", None)
            if target and target in clients:
                try:
                    await clients[target].send(json.dumps(data))
                except Exception as e:
                    logger.warning(f"Direct send to {target} failed: {e!r}")
                continue

            # ③ otherwise broadcast to everyone except sender
            dead = set()
            for cid, peer in list(clients.items()):
                if peer is ws:
                    continue
                try:
                    await peer.send(msg)
                except Exception as e:
                    logger.warning(f"Peer {cid} send failed: {e!r}")
                    dead.add(cid)
            for d in dead:
                clients.pop(d, None)
    except websockets.exceptions.ConnectionClosedOK:
        pass
    except Exception as e:
        logger.exception(f"Unexpected error in handler: {e!r}")
    finally:
        if my_id:
            clients.pop(my_id, None)
        logger.info(f"Client disconnected: {ws.remote_address}")

async def main():
    logger.info("Starting relay on 0.0.0.0:6789")
    async with websockets.serve(handler, "0.0.0.0", 6789):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
