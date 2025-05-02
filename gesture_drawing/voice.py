"""Voice-command listener that now routes transcripts via llm_router."""
from __future__ import annotations

import threading
import speech_recognition as sr
from typing import Callable, Optional

# your new router:
from .llm_router import normalise  

CommandCallback = Callable[[str], None]

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
                    continue
                except sr.RequestError as e:
                    print(f"Speech API error: {e}")
    threading.Thread(target=_listener, daemon=True).start()
