"""
Getting pictures from the camera.

A WiFi camera sends a never-ending stream of pictures (frames). If we only
look at the stream once in a while, old frames pile up and we end up reading
text from the past. So a small helper thread keeps pulling frames off the
stream and we only *decode to colour* the newest one when someone asks for it.
That keeps the picture fresh and the CPU cool.
"""

import os
import sysconfig
import threading
import time

import cv2

from .errors import TextSpotterError


def _check_cv2_build():
    """The UNO Q has no display server, so only opencv-python-headless works.

    If the GUI build (opencv-python) or a system-wide cv2 gets imported
    instead, it dies with "ImportError: libGL.so.1". Catch that here and say
    what to do about it.
    """
    try:
        path = os.path.dirname(os.path.abspath(cv2.__file__))
    except Exception:
        return
    venv = sysconfig.get_path("purelib")
    if venv and not path.startswith(venv):
        raise TextSpotterError(
            "cv2 was loaded from outside this app's venv: " + path + ".\n"
            "The UNO Q needs the headless build. In the board's terminal run:\n"
            "  pip uninstall -y opencv-python && pip install --force-reinstall opencv-python-headless"
        )

    # The GUI build of OpenCV (pulled in by rapidocr_onnxruntime) needs
    # libGL.so.1, which the UNO Q doesn't ship. If it's missing, say so.
    try:
        import ctypes.util

        if ctypes.util.find_library("GL") is None:
            raise TextSpotterError(
                "OpenCV can't load libGL.so.1 - the UNO Q has no display server.\n"
                "One-time fix in the board's terminal (SSH or adb shell):\n"
                "  sudo apt update && sudo apt install -y libgl1"
            )
    except TextSpotterError:
        raise
    except Exception:
        pass


_check_cv2_build()

STREAM_PREFIXES = ("rtsp://", "rtsps://", "http://", "https://", "udp://", "tcp://")


def _is_stream(source):
    return isinstance(source, int) or str(source).lower().startswith(STREAM_PREFIXES)


def open_camera(source):
    """Pick the right helper for whatever kind of camera we were given."""
    if hasattr(source, "capture"):  # the UNO Q's own Camera from App Lab
        return AppLabCamera(source)
    return Camera(source)


class AppLabCamera:
    """Uses the UNO Q's own camera: arduino.app_peripherals.camera.Camera.

    App Lab's Camera only gives a frame when asked. For a WiFi camera the
    frames we don't ask for pile up, so a helper thread keeps asking and we
    always hand out the newest one.
    """

    def __init__(self, camera):
        self.source = camera
        self._cam = camera
        self._frame = None
        self._lock = threading.Lock()
        self._has_frame = threading.Event()
        self._we_started_it = False
        if not camera.is_started():
            try:
                camera.start()
            except Exception as e:
                raise TextSpotterError(
                    f"I can't start the camera: {e}\n"
                    "  - Is the camera switched on and on the same WiFi as the Arduino?\n"
                    "  - Are the address, username and password right?"
                ) from e
            self._we_started_it = True
        self._running = True
        self._thread = threading.Thread(target=self._keep_reading, daemon=True)
        self._thread.start()

    def _keep_reading(self):
        while self._running:
            try:
                frame = self._cam.capture()  # waits by itself to match the camera's fps
            except Exception:
                frame = None
            if frame is None:
                time.sleep(0.05)  # no picture right now - the camera reconnects by itself
                continue
            with self._lock:
                self._frame = frame
            self._has_frame.set()

    def get(self, wait=10.0):
        if not self._has_frame.wait(wait):
            raise TextSpotterError("The camera isn't sending pictures. Is the WiFi signal good?")
        with self._lock:
            return self._frame

    def close(self):
        self._running = False
        self._thread.join(timeout=2)
        if self._we_started_it:
            self._cam.stop()


class Camera:
    """Gives you the newest picture from an RTSP stream, a webcam or an image file."""

    def __init__(self, source, connect_timeout=10.0):
        self.source = source
        self._still = None
        self._cap = None
        self._lock = threading.Lock()
        self._has_frame = threading.Event()
        self._running = False
        self._thread = None
        self._connect_timeout = connect_timeout

        if _is_stream(source):
            self._open_stream()
            self._running = True
            self._thread = threading.Thread(target=self._keep_grabbing, daemon=True)
            self._thread.start()
        else:
            self._still = self._load_picture(source)

    # ---------- image files (great for practising without a camera) ----------

    @staticmethod
    def _load_picture(path):
        if not os.path.exists(str(path)):
            raise TextSpotterError(
                f"I can't find the picture '{path}'. Check the file name, "
                "or give me a camera address that starts with rtsp://"
            )
        picture = cv2.imread(str(path))
        if picture is None:
            raise TextSpotterError(f"'{path}' doesn't look like a picture I can open (try .jpg or .png).")
        return picture

    # ---------- live streams ----------

    def _open_stream(self):
        source = self.source
        if isinstance(source, str) and source.lower().startswith(("rtsp://", "rtsps://")):
            # TCP is slower to start than UDP but WiFi drops UDP packets,
            # which turns pictures into grey smudges. TCP = clean pictures.
            os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

        timeout_ms = int(self._connect_timeout * 1000)
        try:
            cap = cv2.VideoCapture(
                source,
                cv2.CAP_FFMPEG if isinstance(source, str) else cv2.CAP_ANY,
                [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms, cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms],
            )
        except (TypeError, cv2.error):
            cap = cv2.VideoCapture(source)  # older OpenCV without timeout options

        if not cap.isOpened():
            cap.release()
            raise TextSpotterError(
                f"I can't reach the camera at {source}.\n"
                "  - Is the camera switched on?\n"
                "  - Is it on the same WiFi as the Arduino?\n"
                "  - Is the address right? Try opening it in VLC on a computer first."
            )
        # Ask for the smallest possible queue so frames don't pile up.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._cap = cap

    def _keep_grabbing(self):
        failures = 0
        while self._running:
            with self._lock:
                ok = self._cap is not None and self._cap.grab()
            if ok:
                failures = 0
                self._has_frame.set()
                time.sleep(0.001)  # let get() squeeze in
                continue

            failures += 1
            self._has_frame.clear()  # nothing fresh to hand out until the next good grab
            if failures >= 20:  # the stream died - WiFi hiccup? try to reconnect
                self._has_frame.clear()
                with self._lock:
                    if self._cap is not None:
                        self._cap.release()
                    self._cap = None
                time.sleep(2)
                try:
                    with self._lock:
                        self._open_stream()
                    failures = 0
                except TextSpotterError:
                    pass
            else:
                time.sleep(0.05)

    def get(self, wait=10.0):
        """Return the newest picture (a numpy array in BGR colours)."""
        if self._still is not None:
            return self._still.copy()

        deadline = time.monotonic() + wait
        while self._has_frame.wait(max(0.0, deadline - time.monotonic())):
            with self._lock:
                ok, frame = self._cap.retrieve() if self._cap is not None else (False, None)
            if ok and frame is not None:
                return frame
            self._has_frame.clear()  # a broken frame (WiFi hiccup) - wait for the next one
        raise TextSpotterError(
            f"The camera at {self.source} isn't sending pictures. Is the WiFi signal good?"
        )

    def close(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
