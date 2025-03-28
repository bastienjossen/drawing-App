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

        # Dictionaries to track pointers and previous coordinates per hand
        self.pointers = {}       # {hand_index: canvas pointer id}
        self.prev_coords = {}    # {hand_index: (prev_x, prev_y)}

        # Initialize two independent brush colors: brush 1 (hand index 0) and brush 2 (hand index 1)
        self.brush_colors = {0: 'black', 1: 'black'}
        self.default_brush_color = 'black'  # For additional pointers, if any

        self.drawing_enabled = False

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
            # Remove the command prefix and parse for an optional brush specifier.
            command_remainder = command.replace("CHANGE COLOR TO ", "").strip()
            if "BRUSH" in command_remainder:
                # Expected format: "COLOR BRUSH X" where X is 1 or 2.
                parts = command_remainder.split("BRUSH")
                color = parts[0].strip()
                brush_num_str = parts[1].strip()
                try:
                    # Convert brush number (user says "1" or "2") to zero-based index.
                    brush_index = int(brush_num_str) - 1
                except ValueError:
                    print(f"Invalid brush number: {brush_num_str}. Command ignored.")
                    return
                self.change_brush_color(color, brush_index)
            else:
                # If no brush is specified, update the default brush color.
                self.change_brush_color(command_remainder)

    def change_brush_color(self, color, brush_index=None):
        """Change the brush color if valid; if brush_index is provided, update that specific brush."""
        try:
            # Validate the color; this call will raise a TclError if the color is not recognized.
            self.canvas.winfo_rgb(color)
            if brush_index is None:
                self.default_brush_color = color
                print(f"Default brush color changed to {color}")
            else:
                # Only brush indices 0 and 1 are supported.
                if brush_index in (0, 1):
                    self.brush_colors[brush_index] = color
                    print(f"Brush {brush_index + 1} color changed to {color}")
                else:
                    print(f"Invalid brush index: {brush_index + 1}. Command ignored.")
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

        recognized_hand_indexes = []

        if results.multi_hand_landmarks and results.multi_handedness:
            h, w, _ = frame.shape
            # Limit to first two hands
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks[:2], results.multi_handedness[:2]):
                # Use MediaPipe’s “Left” or “Right” label to assign a stable hand_index
                label = handedness.classification[0].label
                # Map left-hand → 0, right-hand → 1
                hand_index = 0 if label == "Left" else 1

                recognized_hand_indexes.append(hand_index)

                self.mp_drawing.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )
                tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                x, y = int(tip.x * w), int(tip.y * h)
                finger_is_straight = self.is_index_finger_raised(hand_landmarks)

                self.move_pointer_on_canvas(
                    hand_index, x, y, w, h, finger_is_straight
                )

        # Remove pointers for hands not detected this frame
        for h_idx in list(self.pointers.keys()):
            if h_idx not in recognized_hand_indexes:
                self.canvas.delete(self.pointers[h_idx])
                self.pointers.pop(h_idx, None)
                self.prev_coords.pop(h_idx, None)

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

        # Select the correct brush color based on hand_index.
        if hand_index in self.brush_colors:
            current_color = self.brush_colors[hand_index]
        else:
            current_color = self.default_brush_color

        # Draw a line from the previous coordinate if drawing is enabled and the finger is straight.
        if self.drawing_enabled and finger_straight:
            if hand_index in self.prev_coords:
                prev_x, prev_y = self.prev_coords[hand_index]
                self.canvas.create_line(prev_x, prev_y, canvas_x, canvas_y, width=2, fill=current_color)
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
