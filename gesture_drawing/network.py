# network.py
import asyncio, json, threading, uuid
import websockets
from queue import Queue

_send_q = Queue()
_recv_q = Queue()
_my_id  = str(uuid.uuid4()) 

async def _ws_loop(uri):
    async with websockets.connect(uri) as ws:
        # ① send one “hello” so the host can map my socket ↔ id
        await ws.send(json.dumps({"type": "hello", "id": _my_id}))
        async def _reader():
            async for msg in ws:
                _recv_q.put(json.loads(msg))
        async def _writer():
            loop = asyncio.get_event_loop()
            while True:
                data = await loop.run_in_executor(None, _send_q.get)
                await ws.send(json.dumps(data))
        await asyncio.gather(_reader(), _writer())

def start_client(uri: str):
    t = threading.Thread(target=lambda: asyncio.run(_ws_loop(uri)), daemon=True)
    t.start()

# helper for directed messages
def send_direct(peer_id: str, payload: dict):
    payload = {"to": peer_id, **payload}
    _send_q.put(payload)


def broadcast_event(data: dict):
    _send_q.put(data)

def get_events() -> list[dict]:
    evs = []
    while True:
        try:
            evs.append(_recv_q.get_nowait())
        except:
            break
    return evs
