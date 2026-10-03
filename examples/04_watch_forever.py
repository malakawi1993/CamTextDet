# Lesson 4: Keep watching.
# Prints the text every time it changes. Press Ctrl+C to stop.

from textspotter import TextSpotter

CAMERA = "rtsp://192.168.1.50:554/stream"

with TextSpotter(CAMERA) as eye:
    for text in eye.watch(every=1):
        print("New text:", text)
