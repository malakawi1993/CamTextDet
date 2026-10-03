import os
import re
import time
from dataclasses import dataclass

import cv2

from . import steps
from .camera import open_camera
from .engines import make_engine
from .errors import TextSpotterError


@dataclass
class Word:
    """One word the camera found."""

    text: str  # the word itself, e.g. "STOP"
    confidence: float  # how sure the computer is, from 0 (guessing) to 100 (certain)
    box: tuple  # where it is in the picture: (x, y, width, height)

    def __str__(self):
        return self.text


class TextSpotter:
    """Point a camera at some text and let your Arduino UNO Q read it.

        eye = TextSpotter("rtsp://192.168.1.50:554/stream")
        print(eye.read())

    camera      - an rtsp:// address, a picture file like "sign.jpg", 0 for a USB webcam,
                  or the UNO Q's own Camera(...) from arduino.app_peripherals.camera
    reader      - "auto" (default), "smart" (finds text anywhere) or "fast" (printed pages)
    cores       - how many of the 4 processor cores reading may use (default 2,
                  so the rest of your project keeps running smoothly)
    picture_size- pictures are shrunk to this width before reading. Smaller = faster,
                  bigger = can read smaller letters
    min_confidence - ignore words the computer is less sure about than this (0-100)
    """

    def __init__(self, camera, reader="auto", cores=2, picture_size=640, min_confidence=50):
        cores = max(1, min(int(cores), os.cpu_count() or 1))
        cv2.setNumThreads(cores)
        self.picture_size = picture_size
        self.min_confidence = min_confidence
        self.reader = make_engine(reader, cores)  # load the reader first: no point connecting otherwise
        self.camera = open_camera(camera)
        self.last_picture = None  # the picture we read last time
        self.last_words = []  # the words we found last time
        self.last_time = 0.0  # how many seconds the last read took

    # ------------------------------------------------------------------ reading

    def read(self):
        """Look through the camera and return all the text as a string (lines separated by \\n)."""
        lines = self._scan()
        return "\n".join(" ".join(w.text for w in line) for line in lines)

    def read_words(self):
        """Return a list of Word objects (text, confidence and where it is)."""
        return [word for line in self._scan() for word in line]

    def find(self, word, text=None):
        """Is this word (or phrase) in front of the camera right now? Returns True or False.

        Capitals and punctuation don't matter: find("stop") matches "STOP!".
        Already called read()? Pass its text to skip reading again: find("stop", text)
        """
        wanted = _simplify(word)
        if not wanted:
            return False
        found = _simplify(self.read() if text is None else text)
        return f" {wanted} " in f" {found} "

    def watch(self, every=1.0, only_new=True):
        """Keep reading forever. Use it in a for-loop:

            for text in eye.watch():
                print(text)

        every    - wait this many seconds between reads (rest time for the processor)
        only_new - only give you text when it changes
        """
        previous = None
        while True:
            started = time.monotonic()
            text = self.read()
            if text and (not only_new or text != previous):
                previous = text
                yield text
            elif not text:
                previous = None
            time.sleep(max(0.0, every - (time.monotonic() - started)))

    # ------------------------------------------------------------------ learning

    def snapshot(self, filename="snapshot.jpg", boxes=True):
        """Save the last picture (with boxes around the words) so you can look at it."""
        if self.last_picture is None:
            self.read()
        picture = steps.draw_boxes(self.last_picture, self.last_words) if boxes else self.last_picture
        cv2.imwrite(filename, picture)
        return filename

    def save_steps(self, folder="steps"):
        """Save one picture for every image-processing step, so you can see how the computer thinks."""
        os.makedirs(folder, exist_ok=True)
        picture = self.camera.get()
        small, _ = steps.shrink(picture, self.picture_size)
        gray = steps.gray(small)
        smooth = steps.smooth(gray)
        bw = steps.black_and_white(smooth)
        lines = self._scan(picture)
        files = {
            "1_camera.jpg": picture,
            "2_smaller.jpg": small,
            "3_gray.jpg": gray,
            "4_smooth.jpg": smooth,
            "5_black_and_white.png": bw,
            "6_found_text.jpg": steps.draw_boxes(picture, [w for line in lines for w in line]),
        }
        for name, img in files.items():
            cv2.imwrite(os.path.join(folder, name), img)
        return [os.path.join(folder, name) for name in files]

    # ------------------------------------------------------------------ the end

    def close(self):
        """Hang up the camera. Call this when you're done."""
        self.camera.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------ inside

    def _scan(self, picture=None):
        """Grab a picture, read it, and return the words grouped into lines (top to bottom)."""
        started = time.monotonic()
        if picture is None:
            picture = self.camera.get()
        small, scale = steps.shrink(picture, self.picture_size)

        lines = {}
        for text, conf, (x, y, w, h), line_id in self.reader.read(small):
            if conf < self.min_confidence:
                continue
            # Put the box back onto the full-size picture.
            box = (int(x / scale), int(y / scale), int(w / scale), int(h / scale))
            lines.setdefault(line_id, []).append(Word(text, round(conf, 1), box))

        ordered = sorted(lines.values(), key=lambda ws: (min(w.box[1] for w in ws), min(w.box[0] for w in ws)))
        ordered = [sorted(ws, key=lambda w: w.box[0]) for ws in ordered]

        self.last_picture = picture
        self.last_words = [w for line in ordered for w in line]
        self.last_time = time.monotonic() - started
        return ordered


def _simplify(text):
    return " ".join(re.sub(r"[^0-9a-z]+", " ", text.lower()).split())


__all__ = ["TextSpotter", "Word", "TextSpotterError"]
