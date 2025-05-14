# gesture_app.py

"""Main application that combines hand tracking, voice and drawing."""
from __future__ import annotations

import math
import random
import time
import tkinter as tk
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Iterable, Sequence

import cv2
import mediapipe as mp

from .drawing import DrawingApp
from .voice import listen_for_commands

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
    "Sun", "Tree", "House", "Car", "Cat", "Dog", "Boat", "Flower", "Cloud", "Star",
    "Fish", "Heart", "Balloon", "Butterfly", "Ice Cream", "Cup", "Book", "Chair", "Cake", "Pencil",
    "Apple", "Moon", "Rainbow", "Bird", "Key", "Umbrella", "Clock", "Camera", "Guitar", "Shoe",
)


class GestureDrawingApp(DrawingApp):
    """Tkinter window driven by hand‑gestures and voice commands."""

    # ------------------------------ life‑cycle ------------------------------
    def __init__(self, master: tk.Tk | tk.Toplevel) -> None:  # noqa: D401
        super().__init__(master)
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
        self.pointer_ids: dict[int, int] = {} 
        self.prev_coords: dict[int, tuple[int,int]] = {}
        self.last_times: dict[int, float] = {}
        self.eraser_width = 20
        self.max_calligraphy_width = 25
        self.min_calligraphy_width = 5
        self.width_scaling = 1.0

        # --- feature toggles ----------------------------------------------
        self.drawing_enabled = False
        self.square_drawing_enabled = False
        self.circle_drawing_enabled = False

        # --- game state ----------------------------------------------------
        self.current_prompt = random.choice(_PROMPTS)

        self.instruction_text = self.canvas.create_text(
            self.master.winfo_width() * 5 // 3,
            30,
            text=self._instruction_banner("Say 'START' to start drawing."),
            font=("Arial", 15),
            fill="black",
            anchor="n",
            justify="center",
        )

        # Start asynchronous voice listener
        listen_for_commands(self._handle_command)

        # Kick‑off periodic update loop
        self._update_frame()

    # ------------------------------ UI helpers -----------------------------
    def _instruction_banner(self, *extra: str) -> str:
        msg = [f"Draw: {self.current_prompt}"] + list(extra)
        return "\n".join(msg)

    def _set_instruction(self, *lines: str) -> None:
        self.canvas.itemconfig(self.instruction_text, text="\n".join(lines))

    # ------------------------------ command handling -----------------------
    def _handle_command(self, raw: str) -> None:
        cmd = raw.upper()
        if cmd == "START":
            self.drawing_enabled = True
            self._set_instruction(
                self._instruction_banner(
                    "Say 'STOP' to stop drawing.",
                    "Say 'SQUARE' or 'CIRCLE' to draw a square or circle.",
                    "Say 'CHANGE BRUSH TO …' or 'CHANGE COLOR TO …'.",
                )
            )
            return
        if cmd == "STOP":
            self.drawing_enabled = False
            self.square_drawing_enabled = self.circle_drawing_enabled = False
            self._set_instruction(self._instruction_banner("Say 'START' to resume."))
            return

        if cmd.startswith("CHANGE BRUSH TO "):
            raw_type = cmd.removeprefix("CHANGE BRUSH TO ").strip().lower()
            try:
                self.brush.kind = BrushType(raw_type)  # type: ignore[arg-type]
            except ValueError:
                print(f"Invalid brush type: {raw_type!r}")
                self._set_instruction(self._instruction_banner(f"Invalid brush type: '{raw_type}'. Try again."))
            return

        if cmd.startswith("CHANGE COLOR TO "):
            self._change_colour(cmd.removeprefix("CHANGE COLOR TO ").strip().lower())
            return
        
        if cmd == "ERASER":
            # Switch into eraser brush immediately
            self.brush.kind = BrushType.ERASER
            self.drawing_enabled = True
            self._set_instruction(
                self._instruction_banner("Eraser ON. Say 'STOP' to stop erasing.")
            )
            return
    
        if cmd == "BRUSH":
            # Open the voice-driven brush selector popup
            from .voice import BrushSelectionPopup
    
            self._set_instruction(
                self._instruction_banner("Say the brush name…")
            )
            BrushSelectionPopup(self.master, self._change_brush_kind)
            return

        if cmd == "SQUARE":
            self._toggle_shape("square")
            return
        if cmd == "CIRCLE":
            self._toggle_shape("circle")
            return

        if cmd.startswith("MY GUESS IS "):
            self._evaluate_guess(cmd.removeprefix("MY GUESS IS ").strip())
            return

    def _change_brush_kind(self, kind: str) -> None:
        """Callback from BrushSelectionPopup with a valid brush name."""
        print(f"[Popup] Selected brush: {kind}")
        self.brush.kind = BrushType(kind)  # kind is already lowercase
        self._set_instruction(
            self._instruction_banner(f"Brush set to {kind}. Say 'STOP' to halt.")
        )
    # ---------------------------------------------------------------------
    def _toggle_shape(self, shape: str) -> None:  # square / circle
        attr = f"{shape}_drawing_enabled"
        active = getattr(self, attr)
        if not active:
            setattr(self, attr, True)
            self.drawing_enabled = False
            self._set_instruction(
                f"{shape.capitalize()} drawing mode ON. Move thumb/index to size.\nSay '{shape.upper()}' again to finalise."
            )
        else:
            setattr(self, attr, False)
            finalize = getattr(self, f"_finalize_{shape}")
            finalize()
            self._set_instruction(f"{shape.capitalize()} finalised. Say '{shape.upper()}' to start anew.")

    def _evaluate_guess(self, guess: str) -> None:
        if guess.lower() == self.current_prompt.lower():
            self._set_instruction(f"✔ Correct! It *was* {self.current_prompt}. Picked a new one.")
            self.canvas.delete("drawing")
            self.current_prompt = random.choice(_PROMPTS)
            self.drawing_enabled = False
        else:
            self._set_instruction(f"✘ '{guess}' is wrong – keep trying!")

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
            self.master.after(10, self._update_frame)
            return

        frame = cv2.flip(frame, 1)
        self.frame = frame  # Store current frame for drawing landmarks
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)

        seen: set[int] = set()
        if result.multi_hand_landmarks:
            for idx, hand in enumerate(result.multi_hand_landmarks):
                seen.add(idx)
                self._handle_hand(hand, frame.shape, idx)

        
        # clean‑up cursors/state for hands that disappeared
        for hid in set(self.pointer_ids) - seen:
            self.canvas.delete(self.pointer_ids.pop(hid))
            self.prev_coords.pop(hid, None)
            self.last_times.pop(hid, None)             # add END
        #----

        self.canvas.tag_raise(self.instruction_text)

        cv2.imshow("Hand Gesture", frame)
        cv2.waitKey(1)
        self.master.after(10, self._update_frame)

    def _handle_hand(self, landmarks: Any, frame_shape: tuple[int, int, int], hand_id:int) -> None:
        self._mpdraw.draw_landmarks(self.frame, landmarks, self._mphands.HAND_CONNECTIONS)
        h, w, _ = frame_shape
        tip = landmarks.landmark[self._mphands.HandLandmark.INDEX_FINGER_TIP]
        x1, y1 = int(tip.x * w), int(tip.y * h)
        finger_straight = self._is_index_straight(landmarks)

        if self.square_drawing_enabled:
            thumb = landmarks.landmark[self._mphands.HandLandmark.THUMB_TIP]
            self._update_square_preview(x1, y1, int(thumb.x * w), int(thumb.y * h), w, h)
        elif self.circle_drawing_enabled:
            thumb = landmarks.landmark[self._mphands.HandLandmark.THUMB_TIP]
            self._update_circle_preview(x1, y1, int(thumb.x * w), int(thumb.y * h), w, h)     
        else:
            self._move_pointer(x1, y1, w, h, finger_straight, hand_id)

    # ------------------------------ drawing primitives --------------------
    def _move_pointer(self, x: int, y: int, frame_w: int, frame_h: int, finger_straight: bool, hand_id:int) -> None:
        cx, cy = self.to_canvas(x, y, frame_w=frame_w, frame_h=frame_h)

        if hand_id not in self.pointer_ids:
            self.pointer_ids[hand_id] = self.canvas.create_oval(
                cx-5, cy-5, cx+5, cy+5, fill="red", outline="", tags="drawing")
        else:
            self.canvas.coords(self.pointer_ids[hand_id],
                               cx-5, cy-5, cx+5, cy+5)

        if self.drawing_enabled and finger_straight:
            draw_func = {
                BrushType.SOLID: self._draw_solid,
                BrushType.AIR: self._draw_air,
                BrushType.TEXTURE: self._draw_texture,
                BrushType.CALLIGRAPHY: self._draw_calligraphy,
                BrushType.BLENDING: self._draw_blending,
                BrushType.SHINING: self._draw_shining,
                BrushType.ERASER: self._draw_eraser,
            }[self.brush.kind]
            draw_func(cx, cy, hand_id)
        self.prev_coords[hand_id] = (cx, cy)

    # -- individual brush implementations ---------------------------------
    def _draw_solid(self, x: int, y: int, hand_id:int) -> None:

        prev = self.prev_coords.get(hand_id)
        if prev:
            self.canvas.create_line(*prev, x, y, width=3,
                                    fill=self.brush.colour, tags="drawing")

    def _draw_air(self, x: int, y: int, hand_id:int) -> None:

        prev = self.prev_coords.get(hand_id)
        if not prev:
            self.prev_coords[hand_id] = (x, y)
            return

        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, 10)
            ox = int(x + math.cos(angle) * radius)
            oy = int(y + math.sin(angle) * radius)
            self.canvas.create_oval(ox, oy, ox + 3, oy + 3, fill=self.brush.colour, tags="drawing")

    def _draw_texture(self, x: int, y: int, hand_id:int) -> None:
        # simple stippled effect – extend as needed
        self.canvas.create_text(x, y, text="✶", fill=self.brush.colour, font=("Arial", 10), tags="drawing")

    # --- calligraphy with dynamic width ----------------------------------
    def _draw_calligraphy(self, x: int, y: int, hand_id:int) -> None:

        prev = self.prev_coords.get(hand_id)
        if not prev:
            self.prev_coords[hand_id] = (x, y)
            return
        width = self._calligraphy_width(hand_id, (x, y))
        offset = width / 2
        px, py = self.prev_coords[hand_id]
        dx, dy = x - px, y - py
        if math.hypot(dx, dy) < 1:
            return
        angle = math.atan2(dy, dx) + math.pi / 4  # 45° nib
        ox, oy = offset * math.cos(angle), offset * math.sin(angle)
        poly = (
            px - ox, py - oy,
            px + ox, py + oy,
            x + ox, y + oy,
            x - ox, y - oy,
        )
        self.canvas.create_polygon(*poly, fill=self.brush.colour, outline=self.brush.colour, tags="drawing")
        self.prev_coords[hand_id] = (x, y)

    def _calligraphy_width(self, curr: tuple[int, int], hand_id:int) -> float:

        now = time.time()
        last = self.last_times.get(hand_id)
        prev = self.prev_coords.get(hand_id)
        if last is None or prev is None:
            self.last_times[hand_id] = now
            return self.max_calligraphy_width
        dt = now - last or 1e-5
        dist = math.hypot(curr[0] - prev[0], curr[1] - prev[1])
        self.last_times[hand_id] = now
        return max(self.min_calligraphy_width,
                self.max_calligraphy_width - dist / dt * self.width_scaling)

    # ---------------------------------------------------------------------
    def _draw_blending(self, x: int, y: int, hand_id:int) -> None:
        for _ in range(10):
            ox = x + random.randint(-3, 3)
            oy = y + random.randint(-3, 3)
            self.canvas.create_oval(ox - 5, oy - 5, ox + 5, oy + 5, fill=self.brush.colour, outline="", stipple="gray50", tags="drawing")

    def _draw_shining(self, x: int, y: int, hand_id:int) -> None:
        for i in range(8):
            ang = (2 * math.pi / 8) * i
            ex = x + 10 * math.cos(ang)
            ey = y + 10 * math.sin(ang)
            self.canvas.create_line(x, y, ex, ey, fill=self.brush.colour, tags="drawing")
        self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=self.brush.colour, outline="", tags="drawing")

    def _draw_eraser(self, x: int, y: int, hand_id:int) -> None:
        prev = self.prev_coords.get(hand_id)
        if prev:
            bg = self.canvas["bg"]
            self.canvas.create_line(*prev, x, y, width=self.eraser_width,
                                    fill=bg, tags="drawing")
    

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
            corners.extend([centre[0] + half_side * math.cos(ang), centre[1] + half_side * math.sin(ang)])
        if getattr(self, "square_preview", None):
            self.canvas.coords(self.square_preview, *corners)
        else:
            self.square_preview = self.canvas.create_polygon(*corners, outline="red", fill="", width=5, tags="drawing")

    def _finalize_square(self) -> None:
        if getattr(self, "square_preview", None):
            self.canvas.itemconfig(self.square_preview, outline="black", fill="", width=5)
            self.square_preview = None

    def _update_circle_preview(self, x1: int, y1: int, x2: int, y2: int, fw: int, fh: int) -> None:
        cx1, cy1 = self.to_canvas(x1, y1, frame_w=fw, frame_h=fh)
        cx2, cy2 = self.to_canvas(x2, y2, frame_w=fw, frame_h=fh)
        cx, cy = (cx1 + cx2) / 2, (cy1 + cy2) / 2
        r = math.hypot(cx2 - cx1, cy2 - cy1) / 2
        bbox = (cx - r, cy - r, cx + r, cy + r)
        if getattr(self, "circle_preview", None):
            self.canvas.coords(self.circle_preview, *bbox)
        else:
            self.circle_preview = self.canvas.create_oval(*bbox, outline="red", fill="", width=5, tags="drawing")

    def _finalize_circle(self) -> None:
        if getattr(self, "circle_preview", None):
            self.canvas.itemconfig(self.circle_preview, outline="black", fill="", width=5)
            self.circle_preview = None

    # --------------------------- misc helpers -----------------------------
    @staticmethod
    def _is_index_straight(landmarks) -> bool:  # Mediapipe landmark list
        tip = landmarks.landmark[mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP]
        dip = landmarks.landmark[mp.solutions.hands.HandLandmark.INDEX_FINGER_DIP]
        return tip.y < dip.y

    # --------------------------- cleanup ----------------------------------
    def __del__(self) -> None:
        if self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()