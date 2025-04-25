import math
import tkinter as tk
import cv2
import mediapipe as mp
from drawing import DrawingApp
from utils import listen_for_commands
import random
import time


class GestureDrawingApp(DrawingApp):
    def __init__(self, master):
        super().__init__(master)
        self.cap = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands()
        self.mp_drawing = mp.solutions.drawing_utils

        self.brush_type = "solid"  # Current active brush type
        self.brush_color = "black"  # Active brush color
        self.prev_coord = None  # Previous (x, y) for solid brush
        self.pointer_id = None  # For visualizing finger position
        self.last_time = None
        self.eraser_width = 20

        self.max_calligraphy_width = 25
        self.min_calligraphy_width = 5
        self.width_scaling = 1

        self.drawing_enabled = False
        self.circle_drawing_enabled = False
        self.square_drawing_enabled = False
        self.guess_drawing_enabled = False

        # Game prompts: 30 easily drawable objects
        self.prompts = [
            "Sun", "Tree", "House", "Car", "Cat", "Dog", "Boat", "Flower", "Cloud", "Star",
            "Fish", "Heart", "Balloon", "Butterfly", "Ice Cream", "Cup", "Book", "Chair", "Cake", "Pencil",
            "Apple", "Moon", "Rainbow", "Bird", "Key", "Umbrella", "Clock", "Camera", "Guitar", "Shoe"
        ]
        self.current_prompt = random.choice(self.prompts)

        # Add instruction text to canvas
        self.instruction_text = self.canvas.create_text(
            self.master.winfo_width() * 5 // 3, 30,
            text=f"Draw: {self.current_prompt}\n"
                 "Say 'START' to start drawing.\n"
                 "Say 'SQUARE' or 'CIRCLE' to draw a square or circle.",
            font=("Arial", 15), fill="black", anchor="n", justify="center"
        )

        # Start listening for voice commands
        listen_for_commands(self.handle_command)

        self.update()

    def handle_command(self, command):
        """Handle voice commands."""
        if command == "START":
            self.drawing_enabled = True
            self.update_instruction(
                "Say 'STOP' to stop drawing.\nSay 'CHANGE BRUSH TO SOLID / AIR / SHINING / CALLIGRAPHY / BLENDING' to "
                "change the brush type. \n Say 'CHANGE BRUSH TO ERASER' to start cleaning")
        elif command == "STOP":
            self.drawing_enabled = False
            self.update_instruction(
                "Say 'START' to start drawing.\nSay 'SQUARE' or 'CIRCLE' to draw a square or circle.")
        elif command.startswith("CHANGE BRUSH TO "):
            brush_type = command.replace("CHANGE BRUSH TO ", "").strip().lower()
            self.change_brush_type(brush_type)
        elif command.startswith("CHANGE COLOR TO "):
            # Remove the command prefix and parse for an optional brush specifier.
            command_remainder = command.replace("CHANGE COLOR TO ", "").strip().lower()
            self.change_brush_color(command_remainder)
        elif command == "SQUARE":
            if not self.square_drawing_enabled:
                print("handle_command: SQUARE recognized!")
                self.drawing_enabled = False
                self.square_drawing_enabled = True
                self.update_instruction(
                    "Square drawing mode on. Move your thumb and index finger to adjust the size.\nSay 'SQUARE' to "
                    "finalize.")

            else:
                self.square_drawing_enabled = False
                self.finalize_square()
                self.update_instruction(
                    "Square drawing finalized.\nSay 'SQUARE' to start again.\nSay 'START' to start drawing.")

        elif command == "CIRCLE":
            if not self.circle_drawing_enabled:
                print("handle_command: CIRCLE recognized!")
                self.drawing_enabled = False
                self.circle_drawing_enabled = True
                self.update_instruction(
                    "Circle drawing mode on. Move your thumb and index finger to adjust the size.\nSay 'CIRCLE' to "
                    "finalize.")
            else:
                self.circle_drawing_enabled = False
                self.finalize_circle()
                self.update_instruction("Circle drawing finalized. Say 'CIRCLE' to start again.")

    def change_brush_color(self, color, brush_index=None):
        """Change the brush color if valid; if brush_index is provided, update that specific brush."""
        try:
            # Validate the color; this call will raise a TclError if the color is not recognized.
            self.canvas.winfo_rgb(color)
            self.brush_color = color
            print(f"Brush color is changed to '{color}'.")
        except tk.TclError:
            print(f"Invalid color: '{color}'. Command ignored.")

    def change_brush_type(self, brush_type):
        if brush_type in ["solid", "air", "texture", "calligraphy", "blending", "shining", "eraser"]:
            self.brush_type = brush_type
            brush_color = self.brush_color
            print(f"Brush type changed to {brush_type}, color is set {brush_color}")
        else:
            print(f"Unknown brush type: {brush_type}")

    def draw_solid_brush(self, x, y):
        if self.prev_coord:
            prev_x, prev_y = self.prev_coord
            self.canvas.create_line(prev_x, prev_y, x, y, width=3, fill=self.brush_color)

    def draw_airbrush(self, x, y):
        dot_size = 3
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0, 10)
            offset_x = int(x + math.cos(angle) * radius)
            offset_y = int(y + math.sin(angle) * radius)
            self.canvas.create_oval(offset_x, offset_y, offset_x + dot_size, offset_y + dot_size, fill=self.brush_color)

    def draw_blending_brush(self, x, y):
        for _ in range(10):
            offset_x = x + random.randint(-3, 3)
            offset_y = y + random.randint(-3, 3)
            radius = 5
            # Create semi-transparent effect using stipple pattern
            self.canvas.create_oval(
                offset_x - radius, offset_y - radius,
                offset_x + radius, offset_y + radius,
                fill=self.brush_color,
                outline='',
                stipple='gray50'  # Tkinter's fake transparency
            )

    def draw_shining_brush(self, x, y):
        rays = 8
        length = 10
        for i in range(rays):
            angle = (2 * math.pi / rays) * i
            end_x = x + length * math.cos(angle)
            end_y = y + length * math.sin(angle)
            self.canvas.create_line(x, y, end_x, end_y, fill=self.brush_color)

        # Add central glow
        self.canvas.create_oval(
            x - 2, y - 2, x + 2, y + 2,
            fill=self.brush_color, outline=''
        )

    def draw_eraser_brush(self, x, y):
        """Erase by drawing a thick line in the canvas’s bg color."""
        if self.prev_coord:
            prev_x, prev_y = self.prev_coord
            bg = self.canvas['bg']  # grab the background color
            self.canvas.create_line(
                prev_x, prev_y, x, y,
                width=self.eraser_width,
                fill=bg,
            )

    def update_calligraphy_width(self, current_coord):
        """
        Computes the new brush width based on the speed of the stroke.
        Slow movements yield larger widths and fast movements yield thinner strokes.
        """
        current_time = time.time()
        if self.last_time is None or self.prev_coord is None:
            # First point of a stroke—set default width.
            self.last_time = current_time
            return self.max_calligraphy_width
        dt = current_time - self.last_time
        if dt <= 0:
            dt = 1e-5  # prevent division by zero

        # Calculate distance moved
        dx = current_coord[0] - self.prev_coord[0]
        dy = current_coord[1] - self.prev_coord[1]
        distance = math.hypot(dx, dy)

        # Speed in pixels per second
        speed = distance / dt

        # Map speed to width: slower speed -> larger width; faster speed -> smaller width.
        # For example, subtract a scaled version of the speed from the maximum, and clamp at the minimum.
        new_width = max(self.min_calligraphy_width, self.max_calligraphy_width - speed * self.width_scaling)

        # Update last_time for next call.
        self.last_time = current_time
        return new_width

    def draw_calligraphy_brush(self, x, y):
        """
        Draws a calligraphy-style stroke segment from the previous coordinate (self.prev_coord)
        to the current point (x, y) using a dynamically adjusted brush width.
        """
        current_point = (x, y)
        # Calculate dynamic brush width based on speed.
        brush_width = self.update_calligraphy_width(current_point)
        half_width = brush_width / 2

        # If there's no previous point, simply set it and exit.
        if not self.prev_coord:
            self.prev_coord = current_point
            return

        # Get the previous coordinate.
        prev_x, prev_y = self.prev_coord

        # Compute movement difference.
        dx = x - prev_x
        dy = y - prev_y
        distance = math.hypot(dx, dy)
        if distance < 1:
            return  # Not enough movement to draw anything

        # Determine the angle of movement.
        move_angle = math.atan2(dy, dx)

        # Set a fixed nib offset angle to simulate the calligraphy pen (e.g., 45° offset).
        nib_offset_angle = math.pi / 4
        nib_angle = move_angle + nib_offset_angle

        # Calculate the offset (half the brush width) along the nib angle.
        offset_x = half_width * math.cos(nib_angle)
        offset_y = half_width * math.sin(nib_angle)

        # Define four corners of the stroke polygon.
        p1 = (prev_x - offset_x, prev_y - offset_y)
        p2 = (prev_x + offset_x, prev_y + offset_y)
        p3 = (x + offset_x, y + offset_y)
        p4 = (x - offset_x, y - offset_y)

        # Draw the calligraphic stroke segment as a polygon.
        self.canvas.create_polygon(
            p1[0], p1[1],
            p2[0], p2[1],
            p3[0], p3[1],
            p4[0], p4[1],
            fill=self.brush_color, outline=self.brush_color
        )

        # Update the previous coordinate for the next segment.
        self.prev_coord = current_point

    def update_square_preview(self, x1, y1, x2, y2, frame_width, frame_height):
        # Get canvas dimensions.
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        cx1, cy1 = self.convert_to_canvas_coords(x1, y1, frame_width, frame_height)
        cx2, cy2 = self.convert_to_canvas_coords(x2, y2, frame_width, frame_height)

        # Calculate diagonal and side length.
        diagonal = math.hypot(cx2 - cx1, cy2 - cy1)
        side_length = diagonal / math.sqrt(2)
        half_side = side_length / 2

        # Compute center of the square.
        cx = (cx1 + cx2) / 2
        cy = (cy1 + cy2) / 2

        # Determine rotation so that the square aligns with the diagonal.
        phi = math.atan2(cy2 - cy1, cx2 - cx1)
        theta = phi - math.pi / 4  # Adjust to rotate the square.

        # Compute the 4 corners.
        corners = []
        for i in range(4):
            angle = theta + i * (math.pi / 2)
            corner_x = cx + half_side * math.cos(angle)
            corner_y = cy + half_side * math.sin(angle)
            corners.extend([corner_x, corner_y])

        # If preview exists, update its coordinates. Otherwise, create it.
        if hasattr(self, 'square_preview') and self.square_preview:
            self.canvas.coords(self.square_preview, *corners)
        else:
            self.square_preview = self.canvas.create_polygon(corners, outline='red', fill='red', width=5)

    def finalize_square(self):
        """
        Finalizes the square drawing by leaving the preview on the canvas as a permanent shape.
        Then reset the preview so a new one can be started.
        """
        if hasattr(self, 'square_preview') and self.square_preview:
            # Change the appearance to indicate finalization.
            self.canvas.itemconfig(self.square_preview, outline='black', fill='', width=5)
            self.square_preview = None

    def update_circle_preview(self, x1, y1, x2, y2, frame_width, frame_height):
        # Get canvas dimensions.
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Convert frame coordinates to canvas coordinates.
        cx1, cy1 = self.convert_to_canvas_coords(x1, y1, frame_width, frame_height)
        cx2, cy2 = self.convert_to_canvas_coords(x2, y2, frame_width, frame_height)

        # Compute the center of the circle (midpoint).
        cx = (cx1 + cx2) / 2
        cy = (cy1 + cy2) / 2

        # Compute the diameter as the distance between the two points.
        diameter = math.hypot(cx2 - cx1, cy2 - cy1)
        radius = diameter / 2

        # Define the bounding box for the oval.
        left = cx - radius
        top = cy - radius
        right = cx + radius
        bottom = cy + radius

        # If a preview already exists, update its coordinates.
        if hasattr(self, 'circle_preview') and self.circle_preview:
            self.canvas.coords(self.circle_preview, left, top, right, bottom)
        else:
            self.circle_preview = self.canvas.create_oval(left, top, right, bottom, outline='red', fill='', width=5)

    def finalize_circle(self):
        if hasattr(self, 'circle_preview') and self.circle_preview:
            self.canvas.itemconfig(self.circle_preview, outline='black', fill='', width=5)
            self.circle_preview = None  # Reset so that a new circle can be created later.

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

        if results.multi_hand_landmarks:

            hand_landmarks = results.multi_hand_landmarks[0]
            # Limit to first two hands

            self.mp_drawing.draw_landmarks(
                frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
            )
            h, w, _ = frame.shape
            tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
            x1, y1 = int(tip.x * w), int(tip.y * h)
            finger_is_straight = self.is_index_finger_raised(hand_landmarks)

            if self.square_drawing_enabled:
                thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                x2, y2 = int(thumb_tip.x * w), int(thumb_tip.y * h)

                self.update_square_preview(x1, y1, x2, y2, w, h)
                self.update_pointer('index', x1, y1, w, h, color='blue')
                self.update_pointer('thumb', x2, y2, w, h, color='blue')

            elif self.circle_drawing_enabled:
                thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                x2, y2 = int(thumb_tip.x * w), int(thumb_tip.y * h)

                self.update_circle_preview(x1, y1, x2, y2, w, h)
                self.update_pointer('index', x1, y1, w, h, color='blue')
                self.update_pointer('thumb', x2, y2, w, h, color='blue')

            else:
                self.move_pointer_on_canvas(x1, y1, w, h, finger_straight=finger_is_straight)

        cv2.imshow('Hand Gesture', frame)
        cv2.waitKey(1)
        self.master.after(10, self.update)

    def move_pointer_on_canvas(self, x, y, frame_width, frame_height, finger_straight):
        """Move a pointer for a given hand; draw a line only if the finger is straight and drawing is enabled."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        canvas_x = int(x * canvas_width / frame_width)
        canvas_y = int(y * canvas_height / frame_height)

        # Create or update the pointer for this hand
        if self.pointer_id is None:
            self.pointer_id = self.canvas.create_oval(
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5,
                fill="red", outline=""
            )
        else:
            self.canvas.coords(
                self.pointer_id,
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5
            )

        # Draw a line from the previous coordinate if drawing is enabled and the finger is straight.
        if self.drawing_enabled and finger_straight:
            if self.brush_type == "solid":
                self.draw_solid_brush(canvas_x, canvas_y)
            elif self.brush_type == "air":
                self.draw_airbrush(canvas_x, canvas_y)
            elif self.brush_type == "texture":
                self.draw_texture_brush(canvas_x, canvas_y)
            elif self.brush_type == "calligraphy":
                self.draw_calligraphy_brush(canvas_x, canvas_y)
            elif self.brush_type == "blending":
                self.draw_blending_brush(canvas_x, canvas_y)
            elif self.brush_type == "shining":
                self.draw_shining_brush(canvas_x, canvas_y)
            elif self.brush_type == "eraser":
                self.draw_eraser_brush(canvas_x, canvas_y)

        self.prev_coord = (canvas_x, canvas_y)

    def convert_to_canvas_coords(self, x, y, frame_width, frame_height):
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        canvas_x = int(x * canvas_width / frame_width)
        canvas_y = int(y * canvas_height / frame_height)
        return canvas_x, canvas_y

    def is_index_finger_raised(self, hand_landmarks):
        tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        dip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_DIP]
        return tip.y < dip.y  # True if fingertip is higher than DIP

    def update_pointer(self, pointer_type, x, y, frame_width, frame_height, color='red'):
        """Update or create a pointer for either 'index' or 'thumb' using canvas coordinates."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        canvas_x = int(x * canvas_width / frame_width)
        canvas_y = int(y * canvas_height / frame_height)

        pointer_attr = f'pointer_{pointer_type}'
        # Check if pointer already exists
        if not hasattr(self, pointer_attr) or getattr(self, pointer_attr) is None:
            # Create a new pointer; for example, 10x10 pixel circle.
            pointer = self.canvas.create_oval(
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5,
                fill=color, outline=""
            )
            setattr(self, pointer_attr, pointer)
        else:
            # Update the pointer position.
            self.canvas.coords(getattr(self, pointer_attr),
                               canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5)

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
