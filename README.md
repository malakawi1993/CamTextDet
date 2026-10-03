# 🔤 TextSpotter: teach your Arduino UNO Q to read!

Point a WiFi camera at some words, and your Arduino tells you what they say.

```python
from textspotter import TextSpotter

eye = TextSpotter("rtsp://192.168.1.50:554/stream")
print(eye.read())
```

That's the whole program. ✨

---

## What can it do?

| Code | What happens |
|---|---|
| `eye.read()` | Gives you all the text it can see, one line per row |
| `eye.find("stop")` | `True` if it sees the word "stop" (capitals and `!?.,` don't matter) |
| `eye.read_words()` | A list of words, each with `.text`, `.confidence` (0-100 % sure) and `.box` (where it is) |
| `for text in eye.watch():` | Keeps reading, and gives you the text every time it changes |
| `eye.snapshot("me.jpg")` | Saves the picture with green boxes around every word |
| `eye.save_steps("steps")` | Saves a picture of **every step** the computer takes to find text |
| `eye.last_time` | How many seconds the last read took |
| `eye.close()` | Hangs up the camera |

No camera yet? Give it a picture instead: `TextSpotter("my_sign.jpg")`.

## How does a computer read? (run `eye.save_steps()` and look!)

1. **Camera:** the picture is just a big grid of numbers, 3 per pixel (blue, green, red).
2. **Smaller:** shrink it. Fewer pixels means less work, so it reads faster.
3. **Gray:** throw away the colours. Letters are shapes, so one brightness number per pixel is enough.
4. **Smooth:** blur away the tiny speckles the camera adds.
5. **Black & white:** every pixel becomes pure black or pure white, letters black and paper white.
6. **Found text:** a trained model (a "neural network") finds the shapes that look like letters and turns them into words.

## Lessons in [examples/](examples/)

1. [01_hello_text.py](examples/01_hello_text.py): read some text
2. [02_see_the_steps.py](examples/02_see_the_steps.py): see how the computer sees
3. [03_secret_word.py](examples/03_secret_word.py): the secret password game
4. [04_watch_forever.py](examples/04_watch_forever.py): keep watching
5. [uno_q_app/](examples/uno_q_app/): a full UNO Q app. The Linux side reads the text, and the LED matrix smiles when it sees the magic word "HELLO".

---

## For grown-ups: setup

The UNO Q has two brains. Reading text from a video stream needs the **Linux side**
(Qualcomm QRB2210, 4 cores), so TextSpotter is a Python library. The **STM32 microcontroller**
side gets the results through the Arduino Bridge (see `examples/uno_q_app`).

### Option A: in Arduino App Lab (recommended)

[examples/uno_q_app](examples/uno_q_app/) follows the standard App Lab layout:

```
uno_q_app/
├── app.yaml               name, icon, description
├── python/
│   ├── main.py            Linux side: Camera -> TextSpotter -> Bridge.call(...)
│   ├── requirements.txt   pip packages (the "smart" reader)
│   └── textspotter/       <- copy the library folder here
└── sketch/
    ├── sketch.ino         MCU side: Bridge.provide("show_text"/"draw") + LED matrix
    └── sketch.yaml
```

1. Copy `examples/uno_q_app` into your App Lab apps and copy `textspotter/` into its `python/` folder.
2. In `python/main.py`, set the camera address, username, password and **fps**.
3. Press **Run**. The text shows up in the Python console and the sketch's Monitor, and the LED
   matrix smiles when it sees the magic word.

TextSpotter accepts App Lab's own camera directly:

```python
from arduino.app_peripherals.camera import Camera
camera = Camera("rtsp://192.168.1.50:554/stream", username="admin", password="secret", fps=25)
eye = TextSpotter(camera)
```

⚠️ Set `fps=` to what the camera really sends (App Lab defaults to 10). If it is lower than the
stream's real rate, App Lab reads frames more slowly than they arrive, unread frames pile up, and
TextSpotter reads text from seconds ago.

### Option B: in the board's terminal (SSH or `adb shell`)

```bash
python3 -m venv ~/textspotter-env && source ~/textspotter-env/bin/activate
pip install ./CamTextDet[smart]          # from a copy of this folder
python -m textspotter rtsp://192.168.1.50:554/stream
```

`python -m textspotter my_sign.jpg --steps` reads a picture and saves the steps.

### The two readers

| `reader=` | Good at | Install |
|---|---|---|
| `"smart"` (RapidOCR / PaddleOCR models) | Text anywhere: signs, boxes, T-shirts, tilted text | `pip install rapidocr_onnxruntime` |
| `"fast"` (Tesseract) | Neat printed pages and flash cards; uses less memory | `sudo apt install tesseract-ocr` + `pip install pytesseract` |
| `"auto"` (default) | Uses smart if installed, otherwise fast | |

### Keeping the board responsive

TextSpotter is built so it never takes over the board:

- **`cores=2`** (default): reading uses at most 2 of the 4 cores. The Linux system, App Lab and
  the Bridge keep the others. Use `cores=1` for the gentlest setting.
- **Fresh frames only:** a background thread drains the stream, so frames never pile up and you
  never read old text. Colour conversion only happens for the frame you actually read.
- **`picture_size=640`**: frames are shrunk before reading. Smaller is faster, but below about
  480 the reader starts losing the spaces between words.
- **Rest between reads:** `watch(every=1)` and the examples sleep between reads, so the CPU isn't
  pinned at 100 %.
- **Use the camera's low-res sub-stream.** This is the biggest win. Decoding a 1080p H.264
  stream costs a lot of CPU on its own, before any reading happens. Most IP cameras have a
  second, smaller stream, e.g. `.../stream2`, `.../sub`, or `.../h264Preview_01_sub`. Check
  your camera's manual.
- RTSP is forced over **TCP**, because WiFi drops UDP packets and smears the picture.
  If the stream drops, it reconnects by itself.

### Troubleshooting

| Message / problem | Fix |
|---|---|
| "I can't reach the camera" | Open the same `rtsp://` address in VLC on a computer. If VLC can't open it, the address or password is wrong. Passwords go in the URL: `rtsp://user:pass@ip:554/...` |
| "I don't have a text reader yet" | Install one of the readers above |
| Text is missed | Bigger letters, more light, hold the paper still, or try `picture_size=960` |
| Wrong words show up | Raise `min_confidence` (default 50), e.g. `TextSpotter(cam, min_confidence=80)` |
| Board feels slow | `cores=1`, use the sub-stream, read less often |

### Running the tests

```bash
pip install -e .[smart,test]
python -m pytest tests
```
