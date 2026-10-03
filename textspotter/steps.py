"""
The image-processing steps, one small function each.

Computers don't "see" a picture like we do - to them it is just a big grid of
numbers. Each step below changes those numbers so the text is easier to find.
Use TextSpotter.save_steps() to look at what every step does!
"""

import cv2


def shrink(picture, max_width=640):
    """Step 1 - make the picture smaller.

    Fewer pixels = less work = faster reading. Text is still readable at 640
    pixels wide as long as it isn't tiny in the picture.
    Returns the smaller picture and how much we shrank it (so we can find the
    text again on the big picture later).
    """
    height, width = picture.shape[:2]
    if width <= max_width:
        return picture, 1.0
    scale = max_width / width
    small = cv2.resize(picture, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)
    return small, scale


def gray(picture):
    """Step 2 - throw away the colours.

    Letters are about shapes, not colours. One number per pixel (how bright
    it is) instead of three (blue, green, red) is 3x less to think about.
    """
    if picture.ndim == 2:
        return picture
    return cv2.cvtColor(picture, cv2.COLOR_BGR2GRAY)


def smooth(gray_picture):
    """Step 3 - blur away the tiny speckles (camera noise) but keep edges sharp."""
    return cv2.bilateralFilter(gray_picture, 5, 50, 50)


def black_and_white(gray_picture):
    """Step 4 - every pixel becomes pure black or pure white.

    The computer picks the best "is it dark or light?" line by itself (this
    trick is called Otsu's method). Then we make sure the paper is white and
    the letters are black, because that's what the text reader likes best.
    """
    _, bw = cv2.threshold(gray_picture, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if bw.mean() < 127:  # mostly black? then it was light text on a dark background
        bw = cv2.bitwise_not(bw)
    return bw


def draw_boxes(picture, words, color=(0, 200, 0)):
    """Final step - draw a box around every word we found, with the word on top."""
    out = picture.copy()
    for word in words:
        x, y, w, h = word.box
        cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        cv2.putText(out, word.text, (x, max(12, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return out
