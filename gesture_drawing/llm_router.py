# llm_router.py
from __future__ import annotations
import requests
from functools import lru_cache
from typing import Optional

# ─── Directly embed your key & endpoint ──────────────────────────────
API_KEY = "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"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """\
You are a command parser. If the message is unrelated to drawing, reply with nothing.

When the user requests a color change, always reply with:
  CHANGE COLOR TO <COLOR>
replacing <COLOR> with the exact color they mention.

When the user requests a brush change but does not name one, reply:
  BRUSH

Do not explain or comment.

Valid commands:
START, STOP, SQUARE, CIRCLE, ERASER, BRUSH,
CHANGE BRUSH TO <BRUSH>, CHANGE COLOR TO <COLOR>,
MY GUESS IS <word>
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
