# Gesture Drawing Application

A voice‑ and gesture‑controlled drawing program that turns your webcam into a *brush*.
It combines **MediaPipe** hand‑tracking, **OpenCV** video capture, **SpeechRecognition** for
voice commands, and a **Tkinter** canvas for rendering.

---

## ✨ Features

* Draw with 7 different brushes (solid, air, texture, calligraphy, blending, shining, eraser)
* Voice commands for starting/stopping, changing colours, switching brushes, and drawing
  squares/circles
* Mini *“guess what I’m drawing”* game with 30 random prompts
* Dynamic calligraphy width based on stroke speed

---

## 📦 Installation

```bash
# 1. Clone the repo
$ git clone https://github.com/your‑user/drawing‑app.git
$ cd drawing‑app

# 2. Create and activate a virtual env (recommended)
$ python -m venv venv
$ source venv/bin/activate  # on Windows: venv\Scripts\activate

# 3. Install Python dependencies
$ pip install -r requirements.txt
```

> **macOS + Continuity Camera**: If you see a deprecation warning about
> `AVCaptureDeviceTypeExternal`, you can ignore it—the app still works fine.

---

## 🚀 Running the App

Two equally valid options:

```bash
# Package style (cleaner)
python -m gesture_drawing

# Direct script (fallback)
python path/to/gesture_drawing/main.py
```

Make sure **one** webcam is connected; the first camera in the device list is used.

---

## 🎤 Voice Command Cheatsheet

| Command                                                                     | Action                                                  |
| --------------------------------------------------------------------------- | ------------------------------------------------------- |
| **START / STOP**                                                            | Enable / disable freehand drawing                       |
| **CHANGE BRUSH TO *solid/air/texture/calligraphy/blending/shining/eraser*** | Switch brushes                                          |
| **CHANGE COLOR TO \<colour>**                                               | Any Tk‑recognised colour name (e.g. `red`, `#ff8800`)   |
| **SQUARE / CIRCLE**                                                         | Toggle shape‑drawing mode (thumb + index controls size) |
| **MY GUESS IS \<word>**                                                     | Guess the current prompt in the mini‑game               |

Unrecognised brush types trigger a friendly message instead of crashing.

---

## 🖱️ Basic Usage Flow

1. **Say “START”** – the red fingertip cursor appears.
2. Raise your **index finger straight** to paint; bend it to stop.
3. Change brushes/colours as you draw.
4. Say **“STOP”** or switch to shape mode when needed.

---

## 📁 Project Structure

```
gesture_drawing/
├── __init__.py            # Package marker & public re‑exports
├── main.py                # Entry‑point (also `python -m gesture_drawing`)
├── gesture_app.py         # Hand‑tracking, brushes, game logic
├── drawing.py             # Generic Tk Canvas wrapper
└── voice.py               # Speech‑recognition listener
requirements.txt           # Third‑party deps (MediaPipe, OpenCV‑Python, etc.)
README.md                  # You’re reading it
```
