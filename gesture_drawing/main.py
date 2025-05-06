# main.py

from __future__ import annotations

import sys
import tkinter as tk

from .gesture_app import GestureDrawingApp


def main() -> None:
    root = tk.Tk()
    app = GestureDrawingApp(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nBye! 👋")
        sys.exit()


if __name__ == "__main__":
    main()