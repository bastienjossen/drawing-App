"""Voice‑command utilities (speech_recognition wrapper)."""
from __future__ import annotations

import threading
from typing import Callable

import speech_recognition as sr


CommandCallback = Callable[[str], None]
_SUPPORTED_PREFIXES = (
    "START",
    "STOP",
    "SQUARE",
    "CIRCLE",
    "CHANGE COLOR TO ",
    "CHANGE BRUSH TO ",
    "MY GUESS IS ",
)


def listen_for_commands(callback: CommandCallback) -> None:
    """Continuously listen and dispatch recognised voice commands.

    The function spawns a **daemon** thread so it never blocks the GUI
    event‑loop.  Any recognised sentence that starts with one of
    *_SUPPORTED_PREFIXES* is forwarded to *callback* **verbatim** so the
    main application can decide what to do next.
    """

    def _listener() -> None:
        recogniser = sr.Recognizer()
        with sr.Microphone() as source:
            recogniser.adjust_for_ambient_noise(source, duration=1)
            print("Listening for commands…")
            while True:
                try:
                    audio = recogniser.listen(source)
                    command = recogniser.recognize_google(audio).strip().upper()
                    print(f"Recognised command: {command}")
                    if command.startswith(_SUPPORTED_PREFIXES):
                        callback(command)
                except sr.UnknownValueError:
                    print("Could not understand the audio – ignored.")
                except sr.RequestError as exc:
                    print(f"Speech‑API request error: {exc}")

    threading.Thread(target=_listener, daemon=True).start()