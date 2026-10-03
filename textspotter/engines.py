"""
The "text readers" (OCR engines). Each one takes a picture and returns the
words it found as (text, confidence 0-100, (x, y, w, h), line_id).

  smart - RapidOCR (PaddleOCR models on ONNX Runtime). Finds text anywhere,
          even on signs, boxes and T-shirts. pip-installable, ~15 MB of models.
  fast  - Tesseract. Very light, best for printed pages and flash cards.
          Needs: sudo apt install tesseract-ocr
"""

import os

from . import steps
from .errors import TextSpotterError


class SmartEngine:
    name = "smart"

    def __init__(self, cores):
        # Must be set before onnxruntime starts its thread pools.
        os.environ["OMP_NUM_THREADS"] = str(cores)
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as e:
            raise TextSpotterError(
                "The 'smart' reader isn't installed. Run:  pip install rapidocr_onnxruntime"
            ) from e
        try:
            self._ocr = RapidOCR(intra_op_num_threads=cores, inter_op_num_threads=1)
        except TypeError:  # older versions don't take thread settings
            self._ocr = RapidOCR()

    def read(self, picture):
        result, _ = self._ocr(picture)
        words = []
        for line_id, (polygon, text, score) in enumerate(result or []):
            xs = [int(p[0]) for p in polygon]
            ys = [int(p[1]) for p in polygon]
            x, y = min(xs), min(ys)
            w, h = max(xs) - x, max(ys) - y
            words.extend(_split_line(text, float(score) * 100, (x, y, w, h), line_id))
        return words


class FastEngine:
    name = "fast"

    def __init__(self, cores, language="eng"):
        os.environ["OMP_THREAD_LIMIT"] = str(cores)  # stop Tesseract using every core
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
        except ImportError as e:
            raise TextSpotterError("The 'fast' reader isn't installed. Run:  pip install pytesseract") from e
        except Exception as e:
            raise TextSpotterError(
                "Tesseract isn't installed on this board. Run:  sudo apt install tesseract-ocr"
            ) from e
        self._tess = pytesseract
        self._language = language

    def read(self, picture):
        bw = steps.black_and_white(steps.smooth(steps.gray(picture)))
        # psm 11 = "sparse text": find text anywhere, not only neat paragraphs.
        data = self._tess.image_to_data(
            bw, lang=self._language, config="--psm 11", output_type=self._tess.Output.DICT
        )
        words = []
        for i, text in enumerate(data["text"]):
            text = text.strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:
                continue
            box = (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
            line_id = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            words.append((text, conf, box, line_id))
        return words


def _split_line(text, conf, box, line_id):
    """RapidOCR finds whole lines - cut them into words with a rough box each."""
    pieces = text.split()
    if len(pieces) <= 1:
        return [(text.strip(), conf, box, line_id)] if text.strip() else []
    x, y, w, h = box
    total = max(1, len(text))
    out, pos = [], 0
    for piece in pieces:
        start = text.index(piece, pos)
        pos = start + len(piece)
        px = x + int(w * start / total)
        pw = max(1, int(w * len(piece) / total))
        out.append((piece, conf, (px, y, pw, h), line_id))
    return out


def make_engine(kind, cores):
    if kind == "smart":
        return SmartEngine(cores)
    if kind == "fast":
        return FastEngine(cores)
    if kind == "auto":
        try:
            return SmartEngine(cores)
        except TextSpotterError:
            try:
                return FastEngine(cores)
            except TextSpotterError:
                raise TextSpotterError(
                    "I don't have a text reader yet! Install one:\n"
                    "  pip install rapidocr_onnxruntime      (smart - recommended)\n"
                    "  sudo apt install tesseract-ocr && pip install pytesseract   (fast)"
                ) from None
    raise TextSpotterError(f"reader must be 'auto', 'smart' or 'fast' - not '{kind}'")
