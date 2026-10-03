"""
TextSpotter - teach your Arduino UNO Q to read!

    from textspotter import TextSpotter

    eye = TextSpotter("rtsp://192.168.1.50:554/stream")
    print(eye.read())

That's it. See README.md for more fun things to try.
"""

from .errors import TextSpotterError
from .spotter import TextSpotter, Word

__all__ = ["TextSpotter", "Word", "TextSpotterError"]
__version__ = "1.0.0"
