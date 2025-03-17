import speech_recognition as sr
import threading

def select_color():
    # Function to select a color for drawing
    pass

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

            while True:
                try:
                    audio = recognizer.listen(source)
                    command = recognizer.recognize_google(audio).strip().upper()

                    if command in ["START", "STOP"]:
                        callback(command)

                except sr.UnknownValueError:
                    pass  # Ignore cases where the audio wasn't recognized

    # Run in a separate thread to prevent blocking the main GUI
    thread = threading.Thread(target=listen, daemon=True)
    thread.start()