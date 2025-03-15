import math
import tkinter as tk
from drawing import DrawingApp
import cv2
import mediapipe as mp

class GestureDrawingApp(DrawingApp):
    def __init__(self, master):
        super().__init__(master)
        self.cap = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.pointer = None
        self.prev_x = None
        self.prev_y = None

        self.update()

    def update(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                # Always get index finger tip
                h, w, _ = frame.shape
                tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                x, y = int(tip.x * w), int(tip.y * h)

                # Determine if the finger is straight
                finger_is_straight = self.is_index_finger_raised(hand_landmarks)

                # Move pointer every time; draw line only if finger is straight
                self.move_pointer_on_canvas(x, y, w, h, finger_is_straight)

        cv2.imshow('Hand Gesture', frame)
        self.master.after(10, self.update)

    def move_pointer_on_canvas(self, x, y, frame_width, frame_height, finger_straight):
        """Move a pointer on the canvas at all times; draw a line only if finger is straight."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        canvas_x = int(x * canvas_width / frame_width)
        canvas_y = int(y * canvas_height / frame_height)

        # Create the pointer if it doesn't exist; otherwise move it
        if self.pointer is None:
            self.pointer = self.canvas.create_oval(
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5,
                fill="red", outline=""
            )
        else:
            self.canvas.coords(
                self.pointer,
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5
            )

        # Draw a line from the previous pointer position to the new one only if finger is straight
        if finger_straight and self.prev_x is not None and self.prev_y is not None:
            self.canvas.create_line(
                self.prev_x, self.prev_y, canvas_x, canvas_y,
                width=2, fill='black'
            )

        self.prev_x, self.prev_y = canvas_x, canvas_y

    def is_index_finger_straight(self, hand_landmarks):
        """Return True if index finger is at or above a certain angle threshold (e.g., 160°)."""
        tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        dip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_DIP]
        pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_PIP]

        v_dip_pip = (dip.x - pip.x, dip.y - pip.y, dip.z - pip.z)
        v_tip_dip = (tip.x - dip.x, tip.y - dip.y, tip.z - dip.z)

        dot_val = (v_dip_pip[0] * v_tip_dip[0] +
                   v_dip_pip[1] * v_tip_dip[1] +
                   v_dip_pip[2] * v_tip_dip[2])
        mag1 = math.sqrt(v_dip_pip[0]**2 + v_dip_pip[1]**2 + v_dip_pip[2]**2)
        mag2 = math.sqrt(v_tip_dip[0]**2 + v_tip_dip[1]**2 + v_tip_dip[2]**2)

        if mag1 == 0 or mag2 == 0:
            return False

        angle = math.degrees(math.acos(dot_val / (mag1 * mag2)))
        return angle >= 60

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