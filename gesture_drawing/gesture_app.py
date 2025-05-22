"""Main application that combines hand tracking, voice and drawing."""
from __future__ import annotations

from . import network
from queue import Queue
import uuid
import math
import random
import time
import tkinter as tk
from PIL import Image, ImageTk
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Iterable, Sequence
from .config import IP4_ADDRESS_OF_SERVER_HOST

import cv2
import mediapipe as mp

from .drawing import DrawingApp
from .voice import listen_for_commands, USE_LLM

__all__ = ["GestureDrawingApp"]


class BrushType(str, Enum):
    SOLID = "solid"
    AIR = "air"
    TEXTURE = "texture"
    CALLIGRAPHY = "calligraphy"
    BLENDING = "blending"
    SHINING = "shining"
    ERASER = "eraser"


@dataclass(slots=True)
class Brush:
    kind: BrushType = BrushType.SOLID
    colour: str = "black"


_PROMPTS: Sequence[str] = (
    "Dog",
    "Fish",
    "Bird",
    "House",
    "Star",
    "Heart",
    "Cloud",
    "Flower",
    "Apple",
    "Boat",
    "Cup",
    "Key",
    "Book",
    "Moon",
    "Tree",
    "Car",
    "Cat",
    "Chair",
    "Shoe",
    "Hat",
    "Bed",
    "Cake",
    "Bell",
    "Box",
    "Pen",
    "Egg",
    "Leaf",
    "Nose",
    "Fork",
    "Hand",
    "Ring",
    "Football",
    "Table",
    "Elephant",
    "Guitar",
    "Piano",
    "Lion",
)



class GestureDrawingApp(DrawingApp):
    """Tkinter window driven by hand‑gestures and voice commands."""

    # ------------------------------ life‑cycle ------------------------------
    def __init__(self, master: tk.Tk | tk.Toplevel) -> None:
        super().__init__(master)

        self.master = master
        self.event_history: list[dict] = [] 

        self._start_reminder_id: str | None = None
        self._next_drawer: str | None = None

        self._game_started   = False 

        # helper: start 10-second prompt countdown ----------------
        def queue_prompt_hide():
            if self._start_reminder_id is not None:
                self.master.after_cancel(self._start_reminder_id)
            self._start_reminder_id = self.master.after(
                10000,
                lambda: self._hide_prompt_if_still_pending()
            )

        self._queue_prompt_hide = queue_prompt_hide  # save as method

        self.client_id = str(uuid.uuid4())
        self.remote_cursors: dict[str, int] = {}  # maps peer_id → canvas item

        self.current_drawer: str = self.client_id  # I start as drawer
        self.is_drawer: bool = True
        self.current_prompt: str = random.choice(_PROMPTS)
        self.round_active = False
        self.prompt_visible = True

        self.master.bind_all("<KeyPress-space>", self._on_space)
        self.master.bind("<ButtonPress-1>", self._on_mouse_down)
        self.master.bind("<B1-Motion>", self._on_mouse_drag)
        self.master.bind("<ButtonRelease-1>", self._on_mouse_up)

        # create a small video widget…
        self.video_label = tk.Label(self.master, bd=2, relief="sunken")
        # …and place it over the canvas at bottom-right
        self.video_label.place(
            relx=1.0, rely=1.0,  # relative to bottom-right of master
            anchor="se",  # align its south-east corner
            width=288, height=162  # whatever small size you like
        )

        # start network client (point to your server)
        network.start_client(f"ws://{IP4_ADDRESS_OF_SERVER_HOST}:6789")
        self.master.after(20, self._poll_network)

        master.title("Gesture Drawing Application")

        # --- camera & MediaPipe setup --------------------------------------
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Cannot open webcam – aborting")
        self._mphands = mp.solutions.hands
        self._hands = self._mphands.Hands()
        self._mpdraw = mp.solutions.drawing_utils

        # --- drawing‑state --------------------------------------------------
        self.brush = Brush()
        self.prev_coord: tuple[int, int] | None = None
        self.pointer_id: int | None = None  # canvas item id for fingertip
        self.last_time: float | None = None
        self.eraser_width = 20
        self.max_calligraphy_width = 25
        self.min_calligraphy_width = 5
        self.width_scaling = 1.0

        # --- feature toggles ----------------------------------------------
        self.drawing_enabled = False
        self.square_drawing_enabled = False
        self.circle_drawing_enabled = False

        # --- game state ----------------------------------------------------

        self.instruction_text = self.canvas.create_text(
            self.master.winfo_width() * 5 // 3,
            30,
            text=self._instruction_banner("Say 'START' to begin the game."),
            font=("Arial", 15),
            fill="black",
            anchor="n",
            justify="center",
        )

        self.master.focus_force()

        # Start asynchronous voice listener
        listen_for_commands(self._handle_command)

        # Kick‑off periodic update loop
        self._update_frame()

    def _hide_prompt_if_still_pending(self):
        # only hide the prompt if it’s still shown and drawing hasn’t started
        if self.prompt_visible and not self.drawing_enabled:
            self.prompt_visible = False
            self._refresh_instruction("Say 'START' to begin drawing.")

    def _on_space(self, event: tk.Event) -> None:
        # decide if we're starting or stopping
        if not self.is_drawer:
            return
        cmd = "START" if not self.drawing_enabled else "STOP"
        # 1) locally apply it
        self._handle_command(cmd)
        # 2) broadcast it so peers pick it up too
        self._broadcast({
            "type": "command",
            "command": cmd,
        })

    def _on_mouse_down(self, event: tk.Event) -> None:
        if not self.is_drawer or not self._game_started:
            return
        # start a new “stroke”
        self.last_x, self.last_y = event.x, event.y

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if not self.is_drawer or not self._game_started:
            return
        # draw locally
        x1, y1 = self.last_x, self.last_y
        x2, y2 = event.x, event.y
        self.canvas.create_line(x1, y1, x2, y2,
                                fill=self.brush.colour,
                                width=3,
                                tags="drawing")
        # broadcast to peers
        self._broadcast({
            "type": "line",
            "coords": [x1, y1, x2, y2],
            "colour": self.brush.colour,
            "width": 3,
        })
        # advance the stroke
        self.last_x, self.last_y = x2, y2

    def _on_mouse_up(self, _event: tk.Event) -> None:
        if not self.is_drawer or not self._game_started:
            return
        # finish stroke
        self.last_x = self.last_y = None

    # ------------------------------ UI helpers -----------------------------
    def _instruction_banner(self, *extra: str) -> str:
        msg = list(extra)
        return "\n".join(msg)

    def _set_instruction(self, *lines: str) -> None:
        self.canvas.itemconfig(self.instruction_text, text="\n".join(lines))

    def _refresh_instruction(self, *extra_lines: str) -> None:
        """Update the instruction text, optionally hiding the prompt line."""
        lines = []
        if self.prompt_visible:
            lines.append(f"Draw: {self.current_prompt}")
        lines.extend(extra_lines)
        self.canvas.itemconfig(self.instruction_text, text="\n".join(lines))

    # ------------------------------ command handling -----------------------
    def _handle_command(self, raw: str) -> None:
        cmd = raw.upper()
        if self.is_drawer:
            if cmd == "START":
                # 1) If the round isn't active, this START just begins the game:
                if not self._game_started:
                    self._game_started = True
                    # only now actually *start* the round,
                    # and if someone was queued as next_drawer, use that
                    self._local_start_round(drawer_id=self._next_drawer)
                    # clear so future rounds default back to you
                    self._next_drawer = None

                    self.round_active = True
                    self.prompt_visible = True

                    self._queue_prompt_hide()          # show prompt 5 seconds
                    return
                self.prompt_visible = False
                # 2) Round is active => now actually enable the brush:
                self.drawing_enabled = True
                self._refresh_instruction(
                    "Say 'STOP' to stop drawing.",
                    "Say 'SQUARE' or 'CIRCLE' to draw a square or circle.",
                    "Say 'CHANGE BRUSH TO …' or 'CHANGE COLOR TO …'.",
                )
                self._broadcast({"type": "command", "command": "START"})
                return
            if cmd == "STOP":
                self.drawing_enabled = False
                self.square_drawing_enabled = self.circle_drawing_enabled = False
                self._refresh_instruction(self._instruction_banner("Say 'START' to resume."))
                self._broadcast({"type": "command", "command": "STOP"})
                return

            if cmd.startswith("CHANGE BRUSH TO "):
                raw_type = cmd.removeprefix("CHANGE BRUSH TO ").strip().lower()
                try:
                    self.brush.kind = BrushType(raw_type)  # type: ignore[arg-type]
                except ValueError:
                    print(f"Invalid brush type: {raw_type!r}")
                    self._refresh_instruction(self._instruction_banner(f"Invalid brush type: '{raw_type}'. Try again."))
                return

            if cmd.startswith("CHANGE COLOR TO "):
                self._change_colour(cmd.removeprefix("CHANGE COLOR TO ").strip().lower())
                return

            if cmd == "ERASER":
                # Switch into eraser brush immediately
                self.brush.kind = BrushType.ERASER
                self.drawing_enabled = True
                self._refresh_instruction(
                    self._instruction_banner("Eraser ON. Say 'STOP' to stop erasing. 'BRUSH' to change back to brush.")
                )
                return

            if cmd == "BRUSH":
                # Open the voice-driven brush selector popup
                from .voice import BrushSelectionPopup

                self._refresh_instruction(
                    self._instruction_banner("Say the brush name…")
                )
                BrushSelectionPopup(self.master, self._change_brush_kind)
                return

            if cmd == "PLACE":
                if self.square_drawing_enabled:
                    # this will call _finalize_square internally
                    self._toggle_shape("square")
                elif self.circle_drawing_enabled:
                    # this will call _finalize_circle internally
                    self._toggle_shape("circle")
                return

            if cmd == "SQUARE":
                self._toggle_shape("square")
                return
            if cmd == "CIRCLE":
                self._toggle_shape("circle")
                return
        else:
            if cmd.startswith("MY GUESS IS "):
                guess = cmd.removeprefix("MY GUESS IS ").strip()
                self._broadcast({
                    "type": "guess",
                    "id": self.client_id,
                    "guess": guess,
                })
                return

    def _send_guess(self, guess: str):
        # evaluate locally
        correct = (guess.lower() == self.current_prompt.lower())
        # broadcast my guess + my id
        self._broadcast({
            "type": "guess",
            "guess": guess,
            "id": self.client_id
        })
        if correct:
            # on correct guess: schedule me as next drawer, but don't start yet
            self._next_drawer = self.client_id
            self.round_active = False
            self.canvas.delete("drawing")
            self.prompt_visible = False
            self._refresh_instruction("✔ You were right! Say 'START' to draw next.")

    def _change_brush_kind(self, kind: str) -> None:
        """Callback from BrushSelectionPopup with a valid brush name."""
        print(f"[Popup] Selected brush: {kind}")
        self.brush.kind = BrushType(kind)  # kind is already lowercase
        self._refresh_instruction(
            self._instruction_banner(f"Brush set to {kind}. Say 'STOP' to halt.")
        )

    # ---------------------------------------------------------------------
    def _toggle_shape(self, shape: str) -> None:  # square / circle
        attr = f"{shape}_drawing_enabled"
        active = getattr(self, attr)
        if not active:
            setattr(self, attr, True)
            self.drawing_enabled = False
            self._refresh_instruction(
                f"{shape.capitalize()} drawing mode ON. Move thumb/index to size.\nSay '{shape.upper()}' again to finalise."
            )
        else:
            setattr(self, attr, False)
            finalize = getattr(self, f"_finalize_{shape}")
            finalize()
            self._refresh_instruction(f"{shape.capitalize()} finalised. Say '{shape.upper()}' to start anew.")

    def _evaluate_guess(self, guess: str) -> None:
        if guess.lower() == self.current_prompt.lower():
            self._refresh_instruction(f"✔ Correct! It *was* {self.current_prompt}. Picked a new one.")
            self.canvas.delete("drawing")
            self.current_prompt = random.choice(_PROMPTS)
            self.drawing_enabled = False

    def _change_colour(self, colour: str) -> None:
        try:
            self.canvas.winfo_rgb(colour)  # validate via Tcl
            self.brush.colour = colour
            print(f"Colour set to {colour!r}")
        except tk.TclError:
            print(f"Invalid colour: {colour!r} – ignored.")

    # ------------------------------ camera loop ---------------------------
    def _update_frame(self) -> None:
        ok, frame = self.cap.read()
        if not ok:
            return
        # flip so it’s a mirror view
        frame = cv2.flip(frame, 1)
        self.frame = frame

        # 1) run Mediapipe on the flipped frame
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)

        # 2) if there's a hand, handle it (this will draw on the Tkinter canvas)
        if result.multi_hand_landmarks:
            lm = result.multi_hand_landmarks[0]
            self._handle_hand(lm, frame.shape)

        # 3) draw the landmark overlay on the frame itself for display
        if result.multi_hand_landmarks:
            for lm in result.multi_hand_landmarks:
                self._mpdraw.draw_landmarks(frame, lm, self._mphands.HAND_CONNECTIONS)

        # downscale the entire frame to fit your little preview box
        small = cv2.resize(frame, (288, 162), interpolation=cv2.INTER_AREA)

        # now convert to PhotoImage
        disp = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(disp)

        imgtk = ImageTk.PhotoImage(image=img)
        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

        # schedule next frame
        self.master.after(10, self._update_frame)

    def _handle_hand(self, landmarks: Any, frame_shape: tuple[int, int, int]) -> None:
        self._mpdraw.draw_landmarks(self.frame, landmarks, self._mphands.HAND_CONNECTIONS)
        h, w, _ = frame_shape
        tip = landmarks.landmark[self._mphands.HandLandmark.INDEX_FINGER_TIP]
        x1, y1 = int(tip.x * w), int(tip.y * h)

        if self.square_drawing_enabled:
            thumb = landmarks.landmark[self._mphands.HandLandmark.THUMB_TIP]
            self._update_square_preview(x1, y1, int(thumb.x * w), int(thumb.y * h), w, h)
        elif self.circle_drawing_enabled:
            thumb = landmarks.landmark[self._mphands.HandLandmark.THUMB_TIP]
            self._update_circle_preview(x1, y1, int(thumb.x * w), int(thumb.y * h), w, h)
        else:
            self._move_pointer(x1, y1, w, h)

    # ------------------------------ drawing primitives --------------------
    def _move_pointer(self, x: int, y: int, frame_w: int, frame_h: int) -> None:
        cx, cy = self.to_canvas(x, y, frame_w=frame_w, frame_h=frame_h)

        if self.pointer_id is None:
            self.pointer_id = self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="red", outline="",
                                                      tags="pointer")
        else:
            self.canvas.coords(self.pointer_id, cx - 5, cy - 5, cx + 5, cy + 5)

        self._broadcast({
            "type": "cursor",
            "id": self.client_id,
            "coords": [cx, cy],
        })

        self.canvas.tag_raise("pointer")

        if self.is_drawer and self.drawing_enabled:
            draw_func = {
                BrushType.SOLID: self._draw_solid,
                BrushType.AIR: self._draw_air,
                BrushType.TEXTURE: self._draw_texture,
                BrushType.CALLIGRAPHY: self._draw_calligraphy,
                BrushType.BLENDING: self._draw_blending,
                BrushType.SHINING: self._draw_shining,
                BrushType.ERASER: self._draw_eraser,
            }[self.brush.kind]
            draw_func(cx, cy)
        self.prev_coord = (cx, cy)

    # -- individual brush implementations ---------------------------------
    def _draw_solid(self, x: int, y: int) -> None:
        if self.prev_coord:
            # local draw
            self.canvas.create_line(*self.prev_coord, x, y,
                                    width=3,
                                    fill=self.brush.colour,
                                    tags="drawing")
            # broadcast to peers
            self._broadcast({
                "type": "line",
                "coords": [*self.prev_coord, x, y],
                "colour": self.brush.colour,
                "width": 3,
            })

    def _draw_air(self, x: int, y: int) -> None:
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, 10)
            ox = int(x + math.cos(angle) * radius)
            oy = int(y + math.sin(angle) * radius)
            self.canvas.create_oval(ox, oy, ox + 3, oy + 3,
                                    fill=self.brush.colour,
                                    tags="drawing")
            self._broadcast({
                "type": "air",
                "coords": [ox, oy, ox + 3, oy + 3],
                "colour": self.brush.colour,
            })

    def _draw_texture(self, x: int, y: int) -> None:
        self.canvas.create_text(x, y,
                                text="✶",
                                fill=self.brush.colour,
                                font=("Arial", 10),
                                tags="drawing")
        self._broadcast({
            "type": "texture",
            "coords": [x, y],
            "colour": self.brush.colour,
        })

    def _draw_calligraphy(self, x: int, y: int) -> None:
        if not self.prev_coord:
            self.prev_coord = (x, y)
            return
        width = self._calligraphy_width((x, y))
        offset = width / 2
        px, py = self.prev_coord
        dx, dy = x - px, y - py
        if math.hypot(dx, dy) < 1:
            return
        angle = math.atan2(dy, dx) + math.pi / 4
        ox, oy = offset * math.cos(angle), offset * math.sin(angle)
        poly = (
            px - ox, py - oy,
            px + ox, py + oy,
            x + ox, y + oy,
            x - ox, y - oy,
        )
        self.canvas.create_polygon(*poly,
                                   fill=self.brush.colour,
                                   outline=self.brush.colour,
                                   tags="drawing")
        self._broadcast({
            "type": "calligraphy",
            "polygon": poly,
            "colour": self.brush.colour,
        })
        self.prev_coord = (x, y)

    def _calligraphy_width(self, curr: tuple[int, int]) -> float:
        now = time.time()
        if self.last_time is None or self.prev_coord is None:
            self.last_time = now
            return self.max_calligraphy_width
        dt = now - self.last_time or 1e-5
        dist = math.hypot(curr[0] - self.prev_coord[0], curr[1] - self.prev_coord[1])
        speed = dist / dt
        self.last_time = now
        return max(self.min_calligraphy_width, self.max_calligraphy_width - speed * self.width_scaling)

    # ---------------------------------------------------------------------

    def _draw_blending(self, x: int, y: int) -> None:
        for _ in range(10):
            ox = x + random.randint(-3, 3)
            oy = y + random.randint(-3, 3)
            self.canvas.create_oval(ox - 5, oy - 5, ox + 5, oy + 5,
                                    fill=self.brush.colour,
                                    outline="",
                                    stipple="gray50",
                                    tags="drawing")
            self._broadcast({
                "type": "blending",
                "coords": [ox, oy],
                "colour": self.brush.colour,
            })

    def _draw_shining(self, x: int, y: int) -> None:
        for i in range(8):
            ang = (2 * math.pi / 8) * i
            ex = x + 10 * math.cos(ang)
            ey = y + 10 * math.sin(ang)
            self.canvas.create_line(x, y, ex, ey,
                                    fill=self.brush.colour,
                                    tags="drawing")
        self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2,
                                fill=self.brush.colour,
                                outline="",
                                tags="drawing")
        self._broadcast({
            "type": "shining",
            "center": [x, y],
            "colour": self.brush.colour,
        })

    def _draw_eraser(self, x: int, y: int) -> None:
        if self.prev_coord:
            bg = self.canvas["bg"]
            self.canvas.create_line(*self.prev_coord, x, y,
                                    width=self.eraser_width,
                                    fill=bg,
                                    tags="drawing")
            self._broadcast({
                "type": "eraser",
                "coords": [*self.prev_coord, x, y],
                "width": self.eraser_width,
            })

        # --------------------------- shape previews ---------------------------

    def _update_square_preview(self, x1: int, y1: int, x2: int, y2: int, fw: int, fh: int) -> None:
        cx1, cy1 = self.to_canvas(x1, y1, frame_w=fw, frame_h=fh)
        cx2, cy2 = self.to_canvas(x2, y2, frame_w=fw, frame_h=fh)
        diag = math.hypot(cx2 - cx1, cy2 - cy1)
        half_side = diag / math.sqrt(2) / 2
        centre = ((cx1 + cx2) / 2, (cy1 + cy2) / 2)
        phi = math.atan2(cy2 - cy1, cx2 - cx1) - math.pi / 4

        corners: list[float] = []
        for i in range(4):
            ang = phi + i * math.pi / 2
            corners.extend([
                centre[0] + half_side * math.cos(ang),
                centre[1] + half_side * math.sin(ang)
            ])

        # ←–– HERE: use the current brush colour for preview
        color = self.brush.colour

        if getattr(self, "square_preview", None):
            self.canvas.coords(self.square_preview, *corners)
        else:
            self.square_preview = self.canvas.create_polygon(
                *corners,
                outline=color,
                fill="",
                width=5,
                tags="drawing"
            )

        self._broadcast({
            "type":   "square_preview",
            "corners": corners,
            "colour": color,
        })

    def _finalize_square(self) -> None:
        if getattr(self, "square_preview", None) is not None:
            corners = self.canvas.coords(self.square_preview)
            final_color = self.brush.colour
            self._broadcast({
                "type": "square_finalize",
                "corners": corners,
                "colour": final_color,
            })

            self.canvas.itemconfig(
                self.square_preview,
                outline=final_color,
                fill="",
                width=5
            )

            self.square_preview = None


    def _update_circle_preview(self, x1: int, y1: int, x2: int, y2: int, fw: int, fh: int) -> None:
        cx1, cy1 = self.to_canvas(x1, y1, frame_w=fw, frame_h=fh)
        cx2, cy2 = self.to_canvas(x2, y2, frame_w=fw, frame_h=fh)
        cx, cy = (cx1 + cx2) / 2, (cy1 + cy2) / 2
        r = math.hypot(cx2 - cx1, cy2 - cy1) / 2
        bbox = (cx - r, cy - r, cx + r, cy + r)

        # ←–– HERE: use the current brush colour for preview
        color = self.brush.colour

        if getattr(self, "circle_preview", None):
            self.canvas.coords(self.circle_preview, *bbox)
        else:
            self.circle_preview = self.canvas.create_oval(
                *bbox,
                outline=color,
                fill="",
                width=5,
                tags="drawing"
            )

        self._broadcast({
            "type": "circle_preview",
            "bbox": bbox,
            "colour": color,
        })

    def _finalize_circle(self) -> None:
        if getattr(self, "circle_preview", None) is not None:
            bbox = self.canvas.coords(self.circle_preview)
            final_color = self.brush.colour
            self._broadcast({
                "type": "circle_finalize",
                "bbox": bbox,
                 "colour": final_color,
            })

            self.canvas.itemconfig(
                self.circle_preview,
                outline=final_color,
                fill="",
                width=5
            )

            self.circle_preview = None

    # --------------------------- cleanup ----------------------------------
    def __del__(self) -> None:
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()

    # --------------------------- network polling ---------------------------
    def _poll_network(self):
        for ev in network.get_events():
            self._apply_event(ev)
        self.master.after(20, self._poll_network)

    def _apply_event(self, ev: dict):
        """Draw whatever your peer just sent."""
        t = ev.get("type")

        if t == "hello" and self.is_drawer:
            network.send_direct(
                ev["id"],
                {
                    "type":   "state_snapshot",
                    "drawer": self.current_drawer,
                    "prompt": self.current_prompt,
                    "history": self.event_history,
                    "game_started": self._game_started,
                    "round_active": self.round_active,
                }
            )
            return
        
        if t == "state_snapshot":
            self._game_started = ev["game_started"]
            self.round_active  = ev["round_active"]
            self.current_drawer = ev["drawer"]
            self.is_drawer = (self.current_drawer == self.client_id)
            self.current_prompt = ev["prompt"]
            self.canvas.delete("drawing")
            for old_ev in ev["history"]:
                self._apply_event(old_ev)          # reuse existing logic
            if self.is_drawer:
                self.prompt_visible = True
                self._refresh_instruction("Say 'START' to begin drawing.")
                self._queue_prompt_hide()
            else:
                self.prompt_visible = False
                self._refresh_instruction(
                    "Opponent is drawing — say 'MY GUESS IS …' to guess!"
                )
            return

        if t == "start_round":
            self._start_new_round(ev["drawer_id"], ev["prompt"])
            return

        if t == "guess" and self.is_drawer:
            if ev["guess"].lower() == self.current_prompt.lower():
                self._broadcast({
                    "type": "correct_guess",
                    "winner_id": ev["id"],
                    "prompt": self.current_prompt
                })

                # ✅ apply the event locally too:
                self._apply_event({
                    "type": "correct_guess",
                    "winner_id": ev["id"],
                    "prompt": self.current_prompt
                })

                # Delay new round start slightly after overlay
                self.master.after(5000, lambda: self._local_start_round(drawer_id=ev["id"]))
            else:
                print(f"Peer {ev['id']} guessed '{ev['guess']}' – incorrect.")
                self._evaluate_guess(ev["guess"])
            return

        if t == "command":
            # a peer hit space (or spoke START/STOP)
            self._handle_command(ev["command"])
            return
        
        if t == "correct_guess":
            winner_id = ev["winner_id"]
            is_you = (winner_id == self.client_id)
            self.canvas.delete("drawing")
            winner_label = "You" if is_you else f"Peer {winner_id}"
            msg = f"{winner_label} guessed right!\nIt was '{ev['prompt']}'"
            self._show_overlay_message(msg)
            return


        if t == "line":
            x1, y1, x2, y2 = ev["coords"]
            self.canvas.create_line(x1, y1, x2, y2,
                                    fill=ev.get("colour", "black"),
                                    width=ev.get("width", 2),
                                    tags="drawing")
        # extend handling for other types as needed
        elif t == "air":
            x1, y1, x2, y2 = ev["coords"]
            self.canvas.create_oval(x1, y1, x2, y2,
                                    fill=ev["colour"],
                                    tags="drawing")

        elif t == "texture":
            x, y = ev["coords"]
            self.canvas.create_text(x, y, text="✶",
                                    fill=ev["colour"],
                                    font=("Arial", 10),
                                    tags="drawing")

        elif t == "calligraphy":
            poly = ev["polygon"]
            self.canvas.create_polygon(*poly,
                                       fill=ev["colour"],
                                       outline=ev["colour"],
                                       tags="drawing")

        elif t == "blending":
            x, y = ev["coords"]
            self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5,
                                    fill=ev["colour"],
                                    stipple="gray50",
                                    tags="drawing")

        elif t == "shining":
            x, y = ev["center"]
            for i in range(8):
                ang = (2 * math.pi / 8) * i
                ex = x + 10 * math.cos(ang)
                ey = y + 10 * math.sin(ang)
                self.canvas.create_line(x, y, ex, ey,
                                        fill=ev["colour"],
                                        tags="drawing")
            self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2,
                                    fill=ev["colour"],
                                    tags="drawing")

        elif t == "eraser":
            x1, y1, x2, y2 = ev["coords"]
            bg = self.canvas["bg"]
            self.canvas.create_line(x1, y1, x2, y2,
                                    width=ev["width"],
                                    fill=bg,
                                    tags="drawing")

        elif t == "square_preview":
            c = ev.get("colour", "red")
            corners = ev["corners"]
            if hasattr(self, "remote_sqprev"):
                self.canvas.coords(self.remote_sqprev, *corners)
            else:
                self.remote_sqprev = self.canvas.create_polygon(*corners,
                                                                outline=c,
                                                                fill="",
                                                                width=5,
                                                                tags="drawing")

        elif t == "square_finalize":
            c = ev.get("colour", "black")
            corners = ev["corners"]
            # remove preview if you like:
            if hasattr(self, "remote_sqprev"):
                self.canvas.delete(self.remote_sqprev)
            self.canvas.create_polygon(*corners,
                                       outline=c,
                                       fill="",
                                       width=5,
                                       tags="drawing")

        elif t == "circle_preview":
            c = ev.get("colour", "red")
            bbox = ev["bbox"]
            if hasattr(self, "remote_circprev"):
                self.canvas.coords(self.remote_circprev, *bbox)
            else:
                self.remote_circprev = self.canvas.create_oval(*bbox,
                                                               outline=c,
                                                               fill="",
                                                               width=5,
                                                               tags="drawing")
        elif t == "circle_finalize":
            c = ev.get("colour", "black")
            bbox = ev["bbox"]
            # remove preview if you like:
            if hasattr(self, "remote_circprev"):
                self.canvas.delete(self.remote_circprev)
            self.canvas.create_oval(*bbox,
                                    outline=c,
                                    fill="",
                                    width=5,
                                    tags="drawing")

        # handle cursor events
        if t == "cursor":
            peer_id = ev["id"]
            x, y = ev["coords"]
            # if we already have an oval for that peer, move it
            if peer_id in self.remote_cursors:
                self.canvas.coords(self.remote_cursors[peer_id],
                                   x - 5, y - 5, x + 5, y + 5
                                   )
            else:
                # create a new small circle in a different color
                oid = self.canvas.create_oval(
                    x - 5, y - 5, x + 5, y + 5,
                    fill="blue", outline="", tags="cursor"
                )
                self.remote_cursors[peer_id] = oid

    def _start_new_round(self, drawer: str, prompt: str):
        self.current_drawer = drawer
        self._game_started = True
        self.current_prompt = prompt
        self.is_drawer = (drawer == self.client_id)
        # only the drawer should see the prompt word
        self.prompt_visible = self.is_drawer
        # reset *everybody's* drawing state
        self.drawing_enabled = False
        self.square_drawing_enabled = False
        self.circle_drawing_enabled = False

        self.canvas.delete("drawing")
        if self.is_drawer:
            self._refresh_instruction(self._instruction_banner("Say 'START' to begin drawing."))
            self.prompt_visible = True        # show the word first
            self._queue_prompt_hide()
        else:
            if USE_LLM:
                self._refresh_instruction("Opponent is drawing — say your guess!")
            else:
                self._refresh_instruction("Opponent is drawing — say 'MY GUESS IS …' to guess!")

    def _local_start_round(self, drawer_id: str = None):
        # pick a word
        word = random.choice(_PROMPTS)
        drawer = drawer_id or self.client_id

        # update UI + state locally
        self._start_new_round(drawer, word)
        self.round_active = True

        # broadcast exactly once
        self._broadcast({
            "type": "start_round",
            "drawer_id": drawer,
            "prompt": word,
        })

    def _broadcast(self, data: dict) -> None:
        """Send an event to peers and keep it in history (except transient ones)."""
        if data["type"] not in ("cursor",):           # cursors don’t matter for replay
            self.event_history.append(data)
        network.broadcast_event(data)

    def _show_overlay_message(self, text: str, duration_ms: int = 5000) -> None:
        """Show a large centered message temporarily."""
        w, h = self.master.winfo_width() // 2, self.master.winfo_height() // 2
        overlay = self.canvas.create_text(
            w, h,
            text=text,
            font=("Arial", 24, "bold"),
            fill="green",
            justify="center",
            tags="overlay"
        )
        self.master.after(duration_ms, lambda: self.canvas.delete(overlay))
