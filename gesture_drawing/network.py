# network.py
import socketio

class NetworkClient:
    def __init__(self, app, server_url="http://localhost:5001"):
        self.app = app
        self.sio = socketio.Client()
        self.sio.on("draw_event", self._on_draw_event)
        self.sio.connect(server_url)

    def emit_draw(self, x1, y1, x2, y2, colour, width):
        msg = dict(x1=x1, y1=y1, x2=x2, y2=y2,
                   colour=colour, width=width)
        self.sio.emit("draw_event", msg)

    def _on_draw_event(self, data):
        # schedule a draw back on the Tkinter thread
        self.app.master.after(0, 
            lambda: self.app.draw_line(**data)
        )
