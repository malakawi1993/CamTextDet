"""Run with:  python -m pytest tests"""

import cv2
import numpy as np
import pytest

from textspotter import TextSpotter, TextSpotterError


def make_sign(path, lines, dark=False):
    bg, fg = (30, 30, 30), (240, 240, 240)
    if not dark:
        bg, fg = fg, bg
    img = np.full((480, 1280, 3), bg, np.uint8)
    for i, line in enumerate(lines):
        cv2.putText(img, line, (60, 150 + i * 150), cv2.FONT_HERSHEY_SIMPLEX, 3, fg, 8)
    cv2.imwrite(str(path), img)
    return str(path)


@pytest.fixture
def sign(tmp_path):
    return make_sign(tmp_path / "sign.png", ["HELLO ROBOT", "STOP HERE"])


def test_read_lines_in_order(sign):
    with TextSpotter(sign) as eye:
        text = eye.read()
    assert text.splitlines() == ["HELLO ROBOT", "STOP HERE"]


def test_light_text_on_dark(tmp_path):
    with TextSpotter(make_sign(tmp_path / "dark.png", ["NIGHT MODE"], dark=True)) as eye:
        assert eye.find("night mode")


def test_find_ignores_case_and_punctuation(sign):
    with TextSpotter(sign) as eye:
        assert eye.find("robot!")
        assert eye.find("Stop here")
        assert not eye.find("banana")
        assert not eye.find("rob")  # whole words only
        assert eye.find("hello", text="Hello, world")


def test_boxes_are_on_the_full_size_picture(sign):
    with TextSpotter(sign, picture_size=640) as eye:  # the 1280-wide sign is read at half size
        words = eye.read_words()
    hello = next(w for w in words if w.text == "HELLO")
    x, y, w, h = hello.box
    assert 30 < x < 120 and 60 < y < 160 and w > 200  # drawn at x=60, ~70-150 high


def test_save_steps(sign, tmp_path):
    with TextSpotter(sign) as eye:
        files = eye.save_steps(str(tmp_path / "steps"))
    assert len(files) == 6
    assert all(cv2.imread(f) is not None for f in files)


def test_friendly_errors(tmp_path):
    with pytest.raises(TextSpotterError, match="can't find the picture"):
        TextSpotter(str(tmp_path / "nope.jpg"))
    with pytest.raises(TextSpotterError, match="reader must be"):
        TextSpotter("x.jpg", reader="magic")


def test_unreachable_camera():
    with pytest.raises(TextSpotterError, match="can't reach the camera"):
        TextSpotter("rtsp://127.0.0.1:1/nothing")
