# llm_router.py
from __future__ import annotations
import requests
from functools import lru_cache
from typing import Optional
import os
import json

# ─── Load config from llm_config.json ────────────────────────────────
_cfg_path = os.path.join(os.path.dirname(__file__), "llm_config.json")
try:
    with open(_cfg_path, "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)
except FileNotFoundError:
    raise RuntimeError(f"Could not find configuration file at {_cfg_path!r}")
except json.JSONDecodeError as e:
    raise RuntimeError(f"Invalid JSON in config file {_cfg_path!r}: {e}")

API_KEY = _cfg.get("API_KEY")
API_URL = _cfg.get(
    "API_URL",
    "https://api.groq.com/openai/v1/chat/completions"
)

if not API_KEY:
    raise RuntimeError(f"`API_KEY` missing from config file {_cfg_path!r}")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

SYSTEM_PROMPT = """\
You are a command parser. If the message is unrelated to drawing, reply with nothing.

When the user requests a color change, always reply with:
  CHANGE COLOR TO <COLOR>
replacing <COLOR> with the exact color they mention.

When the user requests a brush change but does not name one, reply:
  BRUSH

When the user wants to put a square on the canvas, reply:
    SQUARE
    
When the user wants to put a circle on the canvas, reply:
    CIRCLE
    
When the user wants to erase something, reply:
    ERASER
    
When the user wants to start drawing, reply:
    START
    
When the user wants to stop drawing, reply:
    STOP

WHen the user wants to submit his guess, reply:
    MY GUESS IS <word>

Do not explain or comment.
"""

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

def _call_llm(system_prompt: str, user_text: str, max_tokens=15) -> Optional[str]:
    payload = {
        "model": "allam-2-7b",
        "messages": [
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_text},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stop": ["\n"],
    }
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[llm_router] Error contacting LLM: {e}")
        return None

@lru_cache(maxsize=1024)
def normalise(text: str) -> Optional[str]:
    # your existing SYSTEM_PROMPT as before
    reply = _call_llm(SYSTEM_PROMPT, text).upper()
    return None if reply == "NO_COMMAND" else reply

@lru_cache(maxsize=1024)
def normalise_place(text: str) -> Optional[str]:
    PLACE_PROMPT = """\
    You are in shape‐preview mode (square or circle). The user is sizing a shape on the canvas.
    If the message is unrelated or not a command to place the shape, reply with NOTHING.
    If you detect any attempt of finishing the placement of the shape, reply with:
        PLACE
    If the user tells you to put it somewhere (eg. "right there", "there"), reply with:
        PLACE
    Do not explain or comment."""
    reply = _call_llm(PLACE_PROMPT, text)
    if not reply:
        return None
    return reply.strip().upper()

@lru_cache(maxsize=1024)
def normalise_brush(text: str) -> Optional[str]:
    BRUSH_PROMPT = """\
    You are a voice command parser in brush-selection mode.
    If there is no Brush type specified, reply with NOTHING.

    If there is a Brush type specified, reply with the exact name of the brush type.

    if they say are they mean air.

    Brush types include:
    solid, air, texture, calligraphy, blending, shining

    Do not explain or comment.
    """
    reply = _call_llm(BRUSH_PROMPT, text)
    if not reply or reply.strip().lower() == "nothing":
        return None
    return reply.strip().lower()

@lru_cache(maxsize=1024)
def normalise_guess(text: str) -> Optional[str]:
    GUESS_PROMPT = """\
    You are a voice‐guess parser in a Pictionary game.
    When the user speaks a word or phrase intended as their guess for the current drawing,
    you must find the single word the user is guessing and reply with exactly:

    MY GUESS IS <word>

    replacing `<word>` with exactly what they said (do not translate or paraphrase).
    If the utterance is not a guess, reply with:

    NOTHING

    Do not explain or comment."""
    reply = _call_llm(GUESS_PROMPT, text)
    if not reply or reply.strip().lower() == "nothing":
        return None
    return reply.strip().lower()