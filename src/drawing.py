import tkinter as tk
from tkinter import Canvas, BOTH


class DrawingApp:
    def __init__(self, master):
        self.master = master
        self.setup_canvas()

    def setup_canvas(self):
        self.canvas = tk.Canvas(self.master, bg='white', width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # Make sure there are no lines like:
        # self.canvas.bind("<B1-Motion>", self.some_method)
        # self.canvas.bind("<Button-1>", self.some_method)

    def on_button_press(self, event):
        self.last_x, self.last_y = event.x, event.y

    def on_mouse_drag(self, event):
        if self.last_x is not None and self.last_y is not None:
            self.draw_line(self.last_x, self.last_y, event.x, event.y)
            self.last_x, self.last_y = event.x, event.y

    def on_button_release(self, event):
        self.last_x, self.last_y = None, None

    def draw_line(self, x1, y1, x2, y2):
        self.canvas.create_line(x1, y1, x2, y2, fill='black', width=2)

    def clear_canvas(self):
        self.canvas.delete("all")

    def paint_event(self, x, y, frame_width, frame_height):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        canvas_x = int(x * canvas_width / frame_width)
        canvas_y = int(y * canvas_height / frame_height)
        # Debug:
        # print(canvas_x, canvas_y)

        self.canvas.create_oval(canvas_x - 1, canvas_y - 1, canvas_x + 1, canvas_y + 1, fill="black", width=2)
