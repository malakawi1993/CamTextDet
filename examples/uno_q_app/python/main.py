# Text Spotter - the Linux side of the UNO Q.
# Reads text from a WiFi camera, sends it to the sketch, and makes the
# LED matrix smile when it sees the magic word.
#
# Setup: copy the "textspotter" folder into this "python" folder (next to main.py).
#
# Note: requirements.txt pins opencv-python-headless. The UNO Q has no display
# server, so the regular opencv-python build fails with "libGL.so.1 not found".

import time

import numpy as np
from arduino.app_peripherals.camera import Camera
from arduino.app_utils import App, Bridge, Frame, Logger

from textspotter import TextSpotter

logger = Logger("TextSpotter")

MAGIC_WORD = "hello"  # <- change me!

# Your WiFi camera. Put in its address, username and password.
# fps must match what the camera really sends (often 15, 25 or 30), otherwise
# pictures pile up and the Arduino reads text from the past.
camera = Camera("rtsp://192.168.1.50:554/stream", username="admin", password="secret", fps=25)

# cores=2 leaves the other 2 processor cores free for the rest of the board.
eye = TextSpotter(camera, cores=2)

# Pictures for the 8x13 LED matrix (0 = off, 7 = brightest).
SMILE = Frame(np.array([
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 7, 0, 0, 0, 0, 0, 7, 0, 0, 0],
    [0, 0, 0, 7, 0, 0, 0, 0, 0, 7, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 0],
    [0, 0, 7, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0],
    [0, 0, 0, 7, 7, 7, 7, 7, 7, 7, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
], dtype=np.uint8))

LOOKING = Frame(np.array([
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 7, 7, 7, 0, 0, 0, 7, 7, 7, 0, 0],
    [0, 0, 7, 0, 7, 0, 0, 0, 7, 0, 7, 0, 0],
    [0, 0, 7, 7, 7, 0, 0, 0, 7, 7, 7, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 7, 7, 7, 7, 7, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
], dtype=np.uint8))

last_text = ""


def loop():
    global last_text

    text = eye.read()  # look through the camera and read
    if text != last_text:
        if text:
            logger.info(f"I can see: {text}  ({eye.last_time:.1f} s)")
            Bridge.call("show_text", text[:64])  # the sketch prints it on the Monitor
        last_text = text

    if eye.find(MAGIC_WORD, text):  # check the text we already have
        Bridge.call("draw", SMILE.to_board_bytes())
    else:
        Bridge.call("draw", LOOKING.to_board_bytes())

    time.sleep(0.5)  # a little rest so the board stays cool


App.run(user_loop=loop)
