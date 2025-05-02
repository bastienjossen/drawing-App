import speech_recognition as sr
import threading
import tkinter as tk
import difflib

def save_drawing(canvas, filename):
    # Function to save the current drawing to a file
    pass


def load_drawing(filename):
    # Function to load a drawing from a file
    pass


def listen_for_commands(callback):
    """
    Continuously listens for 'START' or 'STOP' voice commands and triggers the callback function.
    """
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    def listen():
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening for commands...")

            while True:
                try:
                    audio = recognizer.listen(source)
                    command = recognizer.recognize_google(audio).strip().upper()
                    print(f"Recognized command: {command}")

                    if command in ["START", "STOP", "SQUARE", "CIRCLE", "BRUSH"]:
                        callback(command)
                    elif command.startswith("CHANGE COLOR TO "):
                        color = command.replace("CHANGE COLOR TO ", "").strip().lower()
                        callback(f"CHANGE COLOR TO {color}")
                    elif command.startswith("MY GUESS IS "):
                        guess = command.replace("MY GUESS IS ", "").strip().lower()
                        callback(f"MY GUESS IS {guess}")

                # debug
                except sr.UnknownValueError:
                    print("Could not understand the audio.")
                except sr.RequestError as e:
                    print(f"Request error: {e}")

    # Run in a separate thread to prevent blocking the main GUI
    thread = threading.Thread(target=listen, daemon=True)
    thread.start()

class BrushSelectionPopup:
    def __init__(self, parent, on_select_callback):
        self.top = tk.Toplevel(parent)
        self.top.title("Select Brush")
        self.top.geometry("300x250")

        self.label = tk.Label(
            self.top,
            text="Choose one of the brushes:\nSolid\nAir\nShining\nCalligraphy\nBlending",
            font=("Arial", 15)
        )
        self.label.pack(pady=20)

        self.callback = on_select_callback
        self.valid_brushes = ["solid", "air", "texture", "calligraphy", "blending", "shining"]

        self.start_listening()

    def start_listening(self):
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()

        def listen():
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                try:
                    print("Listening for brush name...")
                    audio = recognizer.listen(source, timeout=5)
                    command = recognizer.recognize_google(audio).strip().lower()
                    print(f"Brush popup heard: {command}")

                    closest = difflib.get_close_matches(command, self.valid_brushes, n=1, cutoff=0.6)
                    if closest:
                        self.callback(closest[0])
                        self.top.destroy()
                    else:
                        self.label.config(text=f"'{command}' not recognized.\nTry again.")
                        self.top.after(3000, self.top.destroy)

                except sr.UnknownValueError:
                    self.label.config(text="Could not understand.\nTry again.")
                    self.top.after(3000, self.top.destroy)
                except sr.RequestError as e:
                    self.label.config(text=f"Error: {e}")
                    self.top.after(3000, self.top.destroy)

        threading.Thread(target=listen, daemon=True).start()