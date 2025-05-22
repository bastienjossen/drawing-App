# Gesture Drawing Application

A voice‑ and gesture‑controlled drawing program that turns your webcam into a *brush*.
It combines **MediaPipe** hand‑tracking, **OpenCV** video capture, **SpeechRecognition** for
voice commands, and a **Tkinter** canvas for rendering.

---

## ✨ Features

* Draw with 7 different brushes (solid, air, texture, calligraphy, blending, shining, eraser)
* Voice commands for starting/stopping, changing colours, switching brushes, and drawing
  squares/circles
* Mini *“guess what I’m drawing”* game

---

## 📦 Installation

```bash
# 1. Clone the repo
$ git clone https://github.com/your‑user/drawing‑app.git
$ cd drawing‑app

# 2. Install Python dependencies
$ pip install -r requirements.txt
```

### 3. Fill out the config.py file with an API KEY from https://groq.com/ 

### 4. To start remote:
  The host has to run python gesture_drawing/server.py to start the server.
  In the config.py file 
  * the host has to set ` IP4_ADDRESS_OF_SERVER_HOST = "localhost"` `
  * the client has to set it to the ip4 adress of the host. This adress is found by running: **$ ipconfig getifaddr en0** (en0 for WIFI, en1 for LAN) on the host computer (For MacOS). `IP4_ADDRESS_OF_SERVER_HOST = <HOST-IP> `

  after running both programs it should sync as long as they are in the same network (WIFI).

---

## 🚀 Running the App

```bash
# Run without LLM
python -m gesture_drawing

# Run with LLM (API KEY needed)
python -m gesture_drawing --llm

```

Make sure **one** webcam is connected; the first camera in the device list is used.

---

## 🎤 Voice Command Cheatsheet

| Command                                                                     | Action                                                  |
| --------------------------------------------------------------------------- | ------------------------------------------------------- |
| **START / STOP / Spacebar**                                                            | Enable / disable freehand drawing                       |
| **CHANGE BRUSH TO *solid/air/texture/calligraphy/blending/shining/eraser*** | Switch brushes                                          |
| **CHANGE COLOR TO \<colour>**                                               | Any Tk‑recognised colour name (e.g. `red`, `#ff8800`)   |
| **SQUARE / CIRCLE**                                                         | Toggle shape‑drawing mode (thumb + index controls size) |
| **MY GUESS IS \<word>**                                                     | Guess the current prompt in the mini‑game               |

Unrecognised brush types trigger a friendly message instead of crashing.