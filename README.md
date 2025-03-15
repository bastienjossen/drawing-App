# Gesture Drawing Application

## Description
This application uses a webcam to track the index finger and draw lines on a Tkinter canvas when the finger is raised or straight. It relies on MediaPipe for hand detection and OpenCV for video capture.

## Installation
1. Clone or download the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python src/main.py
   ```

## Usage
- Ensure your webcam is connected. 
- Keep your index finger raised; the application draws when your finger is above the DIP joint. 
- Lower or bend the finger to stop drawing.

## Project Structure
```
drawing-app
├── src
│   ├── main.py          # Main gesture-based drawing logic
│   ├── drawing.py       # DrawingApp class for managing the canvas
│   └── utils.py         # (Optional) utility functions
├── requirements.txt     # Dependencies
└── README.md            # Documentation
```