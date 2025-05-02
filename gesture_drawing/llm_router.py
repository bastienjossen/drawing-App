"""Offline LLM router using llama-cpp-python (no torch needed)."""
from __future__ import annotations
from functools import lru_cache
from typing import Optional

from llama_cpp import Llama

# point this at your downloaded .bin/.gguf
MODEL_PATH = "models/phi-3-mini-4.2b-q4.bin"

# load once
_llm = Llama(model_path=MODEL_PATH, n_ctx=512)

_SYSTEM = (
    "You are a command parser for a gesture-drawing app. "
    "Convert the user's utterance into exactly one of:\n"
    "START, STOP, SQUARE, CIRCLE,\n"
    "CHANGE BRUSH TO <solid/air/texture/calligraphy/blending/shining/eraser>,\n"
    "CHANGE COLOR TO <colour>, MY GUESS IS <word>,\n"
    "or NO_COMMAND if none matches.\n"
    "Respond with the command only."
)

@lru_cache(maxsize=512)
def normalise(text: str) -> Optional[str]:
    prompt = f"{_SYSTEM}\nUser: {text}\nAssistant:"
    resp = _llm.create_completion(
        prompt=prompt,
        max_tokens=16,
        temperature=0.0,
        stop=["\n"],
    )
    cmd = resp.choices[0].text.strip().upper()
    return None if cmd == "NO_COMMAND" else cmd
