# voice.py

"""Voice-command utilities (speech_recognition wrapper)."""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional
import tkinter as tk
import difflib

import speech_recognition as sr

# your routers:
from .llm_router import normalise, normalise_brush, normalise_place, normalise_guess

# ── GLOBAL FLAG ────────────────────────────────────────────────────────────────
# When set, the normal listen_for_commands loop will sleep instead of
# processing—so only popup logic runs.
popup_active = threading.Event()

# ── GENERAL LISTENER ───────────────────────────────────────────────────────────
CommandCallback = Callable[[str], None]

USE_LLM = False  # set this in your main.py 

def listen_for_commands(callback: CommandCallback) -> None:
    def _listener() -> None:
        recog = sr.Recognizer()
        with sr.Microphone() as src:
            recog.adjust_for_ambient_noise(src, duration=1)
            print("Listening for commands…")
            while True:
                if popup_active.is_set():
                    time.sleep(0.4)
                    continue

                try:
                    audio      = recog.listen(src)
                    transcript = recog.recognize_google(audio).strip()
                    print(f"[Normal] Heard: {transcript!r}")
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as exc:
                    print(f"Speech-API request error: {exc}")
                    continue

                cmd = None
                if USE_LLM:
                    # shape‐preview uses special “PLACE” parser
                    in_shape = (
                        getattr(callback.__self__, "square_drawing_enabled", False)
                        or getattr(callback.__self__, "circle_drawing_enabled", False)
                    )
                    in_guess_mode = not getattr(callback.__self__, "is_drawer", False)
                    if in_guess_mode:
                        # guess mode uses the normal LLM
                        cmd = normalise_guess(transcript)
                    else:
                        cmd = normalise_place(transcript) if in_shape else normalise(transcript)
                    if cmd:
                        print(f"→ Normalised to: {cmd}")
                else:
                    # exact‐match fallback
                    cand = transcript.strip().upper()
                    VALID = {
                        "START","STOP","SQUARE","CIRCLE",
                        "ERASER","BRUSH", "SQUARE","CIRCLE","PLACE"
                    }
                    if (
                        cand in VALID
                        or cand.startswith("CHANGE BRUSH TO ")
                        or cand.startswith("CHANGE COLOR TO ")
                        or cand.startswith("MY GUESS IS ")
                    ):
                        cmd = cand
                        print(f"→ Exact match: {cmd}")

                if cmd:
                    callback(cmd)
    threading.Thread(target=_listener, daemon=True).start()


# ── BRUSH POPUP ────────────────────────────────────────────────────────────────
class BrushSelectionPopup:
    """Popup that listens for a brush name (via LLM) and returns the match."""
    def __init__(self, parent: tk.Tk | tk.Toplevel, on_select: Callable[[str], None]):
        # SIGNAL: enter brush-popup mode (mute normal listener)
        popup_active.set()

        self.top = tk.Toplevel(parent)
        self.top.title("Select Brush")
        self.top.geometry("300x250")
        # ensure we clear the flag even if user closes window manually
        self.top.protocol("WM_DELETE_WINDOW", self._on_close)

        self.prompt_text = (
            "Say the brush name:\n"
            "Solid, Air, Texture,\n"
            "Calligraphy, Blending, Shining"
        )
        self.label = tk.Label(
            self.top,
            text=self.prompt_text,
            font=("Arial", 12),
            wraplength=280,
            justify="center"
        )
        self.label.pack(pady=20)

        self.on_select = on_select
        self.valid = {"solid", "air", "texture", "calligraphy", "blending", "shining"}

        # start the popup-specific listener
        self._listen_for_choice()

    def _on_close(self):
        """Clear the flag and destroy if popup closed manually."""
        popup_active.clear()
        self.top.destroy()

    def _listen_for_choice(self):
        recog = sr.Recognizer()
        mic   = sr.Microphone()

        def _worker():
            with mic as src:
                recog.adjust_for_ambient_noise(src, duration=1)
                try:
                    audio = recog.listen(src, timeout=10)
                    transcript = recog.recognize_google(audio).strip()
                    print(f"[BrushPopup] Heard: {transcript!r}")

                    # use your brush-only LLM
                    brush = normalise_brush(transcript)

                    if brush in self.valid:
                        print(f"[BrushPopup] Selected brush: {brush}")
                        # SIGNAL: exit brush-popup mode
                        popup_active.clear()
                        self.on_select(brush)
                        self.top.destroy()
                        return
                    else: print(f"[BrushPopup] Invalid brush: {brush}")

                    # invalid input → prompt retry
                    self.label.config(
                        text=f"‘{transcript}’ not a brush.\nPlease try again."
                    )
                except sr.UnknownValueError:
                    self.label.config(text="Could not understand.\nPlease try again.")
                except Exception as e:
                    self.label.config(text=f"Error: {e}\nPlease try again.")

            # after 2 s, reset prompt and listen again
            self.top.after(
                2000,
                lambda: (
                    self.label.config(text=self.prompt_text),
                    self._listen_for_choice()
                )
            )

        threading.Thread(target=_worker, daemon=True).start()
