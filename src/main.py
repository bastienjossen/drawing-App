import math
import tkinter as tk
import cv2
import mediapipe as mp
from drawing import DrawingApp
from utils import listen_for_commands

class GestureDrawingApp(DrawingApp):
    def __init__(self, master):
        super().__init__(master)
        self.cap = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.mp_drawing = mp.solutions.drawing_utils

        # Use dictionaries to track pointers and previous coordinates for each hand
        self.pointers = {}       # {hand_index: canvas_pointer_id}
        self.prev_coords = {}    # {hand_index: (prev_x, prev_y)}

        self.drawing_enabled = False
        self.brush_color = 'black'

        # Add instruction text to canvas
        self.instruction_text = self.canvas.create_text(
            self.master.winfo_width() // 2, 30,
            text="Say 'START' to start drawing", font=("Arial", 15), fill="gray", anchor="n"
        )

        # Start listening for voice commands
        listen_for_commands(self.handle_command)

        self.update()

    def handle_command(self, command):
        """Handle voice commands."""
        if command == "START":
            self.drawing_enabled = True
            self.update_instruction("Say 'STOP' to stop drawing")
        elif command == "STOP":
            self.drawing_enabled = False
            self.update_instruction("Say 'START' to start drawing")
        elif command.startswith("CHANGE COLOR TO"):
            color = command.replace("CHANGE COLOR TO ", "")
            self.change_brush_color(color)

    def change_brush_color(self, color):
        """Change the brush color if valid; otherwise, ignore the command."""
        try:
            # Validate the color; will raise a TclError if invalid.
            self.canvas.winfo_rgb(color)
            self.brush_color = color
            print(f"Brush color changed to {color}")
        except tk.TclError:
            print(f"Invalid color: '{color}'. Command ignored.")

    def update_instruction(self, text):
        """Update the instruction text on the canvas dynamically."""
        self.canvas.itemconfig(self.instruction_text, text=text)

    def update(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            h, w, _ = frame.shape
            # Enumerate hands so each one has its own index
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                x, y = int(tip.x * w), int(tip.y * h)
                finger_is_straight = self.is_index_finger_raised(hand_landmarks)
                self.move_pointer_on_canvas(idx, x, y, w, h, finger_is_straight)

        cv2.imshow('Hand Gesture', frame)
        self.master.after(10, self.update)

    def move_pointer_on_canvas(self, hand_index, x, y, frame_width, frame_height, finger_straight):
        """Move a pointer for a given hand; draw a line only if the finger is straight and drawing is enabled."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        canvas_x = int(x * canvas_width / frame_width)
        canvas_y = int(y * canvas_height / frame_height)

        # Create or update the pointer for this hand
        if hand_index not in self.pointers:
            pointer_id = self.canvas.create_oval(
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5,
                fill="red", outline=""
            )
            self.pointers[hand_index] = pointer_id
        else:
            self.canvas.coords(
                self.pointers[hand_index],
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5
            )

        # Draw a line from the previous coordinate if drawing is enabled and the finger is straight
        if self.drawing_enabled and finger_straight:
            if hand_index in self.prev_coords:
                prev_x, prev_y = self.prev_coords[hand_index]
                self.canvas.create_line(prev_x, prev_y, canvas_x, canvas_y, width=2, fill=self.brush_color)

        # Update the previous coordinate for this hand
        self.prev_coords[hand_index] = (canvas_x, canvas_y)

    def is_index_finger_raised(self, hand_landmarks):
        tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        dip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_DIP]
        return tip.y < dip.y  # True if fingertip is higher than DIP

    def __del__(self):
        self.cap.release()
        cv2.destroyAllWindows()

def main():
    root = tk.Tk()
    root.title("Gesture Drawing Application")
    app = GestureDrawingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()