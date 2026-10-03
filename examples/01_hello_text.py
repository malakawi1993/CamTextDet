# Lesson 1: Read some text!
# Hold a piece of paper with BIG letters in front of the camera and run this.

from textspotter import TextSpotter

CAMERA = "rtsp://192.168.1.50:554/stream"  # <- change this to your camera's address

eye = TextSpotter(CAMERA)

text = eye.read()
print("I can see:", text)
print("That took", round(eye.last_time, 2), "seconds")

eye.close()
