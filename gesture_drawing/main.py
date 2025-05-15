# main.py

from __future__ import annotations
import sys
import argparse
import tkinter as tk

from . import voice

from .gesture_app import GestureDrawingApp

def main() -> None:
    # 1. parse CLI
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Use the LLM to normalise voice commands",
    )
    args = parser.parse_args()

    # 2. set the global in voice.py
    voice.USE_LLM = args.llm

    # 3. start your app
    root = tk.Tk()
    app = GestureDrawingApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nBye! 👋")
        sys.exit()

if __name__ == "__main__":
    main()