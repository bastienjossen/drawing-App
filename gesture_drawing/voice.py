# voice.py

"""Voice‑command utilities (speech_recognition wrapper)."""
from __future__ import annotations

import threading
from typing import Callable
import tkinter as tk
import difflib

import speech_recognition as sr
from typing import Callable, Optional

# your new router:
from .llm_router import normalise  

CommandCallback = Callable[[str], None]
_SUPPORTED_PREFIXES = (
    "START",
    "STOP",
    "SQUARE",
    "CIRCLE",
    "BRUSH",
    "ERASER",
    "CHANGE COLOR TO ",
    "CHANGE BRUSH TO ",
    "MY GUESS IS ",
)

def listen_for_commands(callback: CommandCallback) -> None:
    """Continuously listen, normalise via local model, then dispatch."""
    def _listener() -> None:
        recog = sr.Recognizer()
        with sr.Microphone() as src:
            recog.adjust_for_ambient_noise(src, duration=1)
            print("Listening for commands…")
            while True:
                try:
                    audio = recog.listen(src)
                    transcript = recog.recognize_google(audio).strip()
                    print(f"Heard: {transcript!r}")
                    cmd = normalise(transcript)
                    if cmd:
                        print(f"→ Normalised to: {cmd}")
                        callback(cmd)
                except sr.UnknownValueError:
                    print("Could not understand the audio – ignored.")
                except sr.RequestError as exc:
                    print(f"Speech‑API request error: {exc}")

    threading.Thread(target=_listener, daemon=True).start()

class BrushSelectionPopup:
    """Popup that listens for a brush name and returns the closest match."""
    def __init__(self, parent: tk.Tk | tk.Toplevel, on_select: Callable[[str], None]):
        self.top = tk.Toplevel(parent)
        self.top.title("Select Brush")
        self.top.geometry("300x250")

        self.label = tk.Label(
            self.top,
            text="Say the brush name:\nSolid, Air, Texture,\nCalligraphy, Blending, Shining",
            font=("Arial", 12), wraplength=280, justify="center"
        )
        self.label.pack(pady=20)

        self.on_select = on_select
        self.valid = ["solid", "air", "texture", "calligraphy", "blending", "shining"]

        # Kick off the worker thread
        self._listen_for_choice()

    def _listen_for_choice(self):
        recog = sr.Recognizer()
        mic   = sr.Microphone()

        def _worker():
            cmd = ""
            with mic as src:
                recog.adjust_for_ambient_noise(src, duration=0.5)
                try:
                    audio = recog.listen(src, timeout=5)
                    cmd = recog.recognize_google(audio).strip().lower()
                    match = difflib.get_close_matches(cmd, self.valid, n=1, cutoff=0.6)
                    if match:
                        # valid brush name picked
                        self.on_select(match[0])
                        self.top.destroy()
                        return
                    # unrecognized word
                    self.label.config(text=f"'{cmd}' not recognized.\nClosing…")
                except sr.UnknownValueError:
                    self.label.config(text="Could not understand.\nClosing…")
                except Exception as e:
                    self.label.config(text=f"Error: {e}\nClosing…")
                finally:
                    # always close after 2 s
                    self.top.after(2000, self.top.destroy)

        threading.Thread(target=_worker, daemon=True).start()
