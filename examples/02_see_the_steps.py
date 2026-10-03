# Lesson 2: How does a computer see?
# This saves a picture for every step into a folder called "steps".
# Open them one by one: colour -> smaller -> gray -> smooth -> black & white -> found text!

from textspotter import TextSpotter

CAMERA = "rtsp://192.168.1.50:554/stream"

eye = TextSpotter(CAMERA)

for picture in eye.save_steps("steps"):
    print("Saved", picture)

for word in eye.read_words():
    print(f"{word.text:15} I'm {word.confidence:.0f}% sure. It's at {word.box}")

eye.close()
