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

@lru_cache(maxsize=1024)
def normalise(text: str) -> Optional[str]:
    payload = {
        # "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "model": "allam-2-7b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": text},
        ],
        "max_tokens": 15,
        "temperature": 0.0,
        "stop": ["\n"],
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=10)
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"].strip().upper()
        return None if reply == "NO_COMMAND" else reply
    except Exception as e:
        print(f"[llm_router] Error contacting LLM: {e}")
        return None
    
def normalise_brush(text: str) -> Optional[str]:
    BRUSH_PROMPT = """\
    You are a voice command parser in brush-selection mode.
    If the message is unrelated or there is no Brush type specified, reply with NOTHING.

    VALID BRUSH TYPES:
    solid, air, texture, calligraphy, blending, shining

    Do not explain or comment.
    """

    payload = {
        "model": "allam-2-7b",
        "messages": [
            {"role": "system", "content": BRUSH_PROMPT},
            {"role": "user", "content": f"Input: {text.strip()}\nBrush:"},
        ],
        "max_tokens": 15,
        "temperature": 0.0,
        "stop": ["\n"]
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=5)
        resp.raise_for_status()
        reply = resp.json()["choices"][0]["message"]["content"].strip().lower()
        return reply if reply != "NOTHING" else None
    except Exception as e:
        print(f"[llm_router] Error in brush parser: {e}")
        return None
