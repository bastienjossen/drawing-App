"""Generic Tkinter canvas that other classes can extend."""
from __future__ import annotations

import tkinter as tk
from tkinter import BOTH, Canvas


class DrawingApp:  # noqa: D101 (simple base‑class)
    def __init__(self, master: tk.Tk | tk.Toplevel) -> None:
        self.master = master
        self.canvas: Canvas = tk.Canvas(self.master, bg="white", width=800, height=600)
        self.canvas.pack(fill=BOTH, expand=True)

    # -----------------------------------------------------------------
    # Mouse fallback – *unused* in the gesture UI but handy for testing.
    # -----------------------------------------------------------------
    def on_button_press(self, event):  # type: ignore[override]
        self.last_x, self.last_y = event.x, event.y  # attributes created on‑the‑fly

    def on_mouse_drag(self, event):  # type: ignore[override]
        if getattr(self, "last_x", None) is not None:
            self.draw_line(self.last_x, self.last_y, event.x, event.y)
            self.last_x, self.last_y = event.x, event.y

    def on_button_release(self, _event):  # type: ignore[override]
        self.last_x = self.last_y = None

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------
    def draw_line(self, x1: int, y1: int, x2: int, y2: int, *, colour: str = "black", width: int = 2) -> None:
        self.canvas.create_line(x1, y1, x2, y2, fill=colour, width=width, tags="drawing")

    def clear_canvas(self) -> None:
        self.canvas.delete("all")

    # Mapping helpers for camera→canvas coordinates – used by subclasses.
    def to_canvas(self, x: int, y: int, *, frame_w: int, frame_h: int) -> tuple[int, int]:
        w = self.canvas.winfo_width() or 1  # avoid division‑by‑zero on startup
        h = self.canvas.winfo_height() or 1
        return int(x * w / frame_w), int(y * h / frame_h)