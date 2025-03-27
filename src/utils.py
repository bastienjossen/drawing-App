import speech_recognition as sr
import threading
import queue
import sounddevice as sd
import vosk
import json
import threading
import os

def save_drawing(canvas, filename):
    # Function to save the current drawing to a file
    pass

def load_drawing(filename):
    # Function to load a drawing from a file
    pass


def listen_for_commands(callback):
    model_path = os.path.join(os.path.dirname(__file__), "../models/vosk-model-small-en-us-0.15")
    model = vosk.Model(model_path)
    q = queue.Queue()

    def audio_callback(indata, frames, time, status):
        if status:
            print(status)
        q.put(bytes(indata))

    def recognition_loop():
        with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                               channels=1, callback=audio_callback):
            rec = vosk.KaldiRecognizer(model, 16000)
            print("Listening for commands...")

            while True:
                data = q.get()
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").upper()
                    print("Heard:", text)

                    if text == "START":
                        callback("START")
                    elif text == "STOP":
                        callback("STOP")
                    elif text.startswith("CHANGE COLOR TO"):
                        # Extract color
                        color = text.replace("CHANGE COLOR TO", "").strip().lower()
                        callback(f"CHANGE COLOR TO {color}")

    threading.Thread(target=recognition_loop, daemon=True).start()