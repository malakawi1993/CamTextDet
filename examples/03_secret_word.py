# Lesson 3: The secret password game.
# Write a word on a card. The Arduino only says "Welcome!" if it sees the secret word.

import time

from textspotter import TextSpotter

CAMERA = "rtsp://192.168.1.50:554/stream"
SECRET = "banana"

eye = TextSpotter(CAMERA)

print("Show me the password...")
while True:
    if eye.find(SECRET):
        print("Welcome, friend!")
        eye.snapshot("friend.jpg")
        break
    time.sleep(1)  # rest a little so the Arduino stays cool

eye.close()
