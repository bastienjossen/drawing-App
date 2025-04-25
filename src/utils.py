import speech_recognition as sr
import threading


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

                    if command in ["START", "STOP", "SQUARE", "CIRCLE"]:
                        callback(command)
                    elif command.startswith("CHANGE COLOR TO "):
                        color = command.replace("CHANGE COLOR TO ", "").strip().lower()
                        callback(f"CHANGE COLOR TO {color}")
                    elif command.startswith("CHANGE BRUSH TO "):
                        brush_type = command.replace("CHANGE BRUSH TO ", "").strip().lower()
                        callback(f"CHANGE BRUSH TO {brush_type}")
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
