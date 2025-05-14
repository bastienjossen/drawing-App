# server.py
import socketio
import eventlet

sio = socketio.Server(cors_allowed_origins="*")
app = socketio.WSGIApp(sio)

@sio.event
def connect(sid, environ):
    print("→ Client connected:", sid)

@sio.event
def draw_event(sid, data):
    # forward to everyone except the sender
    sio.emit("draw_event", data, skip_sid=sid)

@sio.event
def disconnect(sid):
    print("← Client disconnected:", sid)

if __name__ == "__main__":
    print("Starting relay on http://0.0.0.0:5001")
    eventlet.wsgi.server(eventlet.listen(("", 5001)), app)