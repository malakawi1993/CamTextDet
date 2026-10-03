"""Quick test from the terminal:

    python -m textspotter rtsp://192.168.1.50:554/stream
    python -m textspotter my_sign.jpg --steps
"""

import argparse
import sys

from . import TextSpotter, TextSpotterError


def main():
    parser = argparse.ArgumentParser(prog="textspotter", description="Read text from a camera or picture.")
    parser.add_argument("camera", help="rtsp:// address, picture file, or 0 for a USB webcam")
    parser.add_argument("--reader", default="auto", choices=["auto", "smart", "fast"])
    parser.add_argument("--cores", type=int, default=2)
    parser.add_argument("--every", type=float, default=1.0, help="seconds between reads")
    parser.add_argument("--steps", action="store_true", help="save the image-processing steps and stop")
    args = parser.parse_args()

    camera = int(args.camera) if args.camera.isdigit() else args.camera
    is_live = isinstance(camera, int) or "://" in camera
    try:
        with TextSpotter(camera, reader=args.reader, cores=args.cores) as eye:
            print(f"Using the '{eye.reader.name}' reader.")
            if args.steps or not is_live:
                if args.steps:
                    for path in eye.save_steps():
                        print("saved", path)
                print(eye.read() or "(no text found)")
                print(f"took {eye.last_time:.2f} s")
                return
            print("Watching... press Ctrl+C to stop.")
            for text in eye.watch(every=args.every):
                print(f"--- ({eye.last_time:.2f} s)\n{text}")
    except TextSpotterError as e:
        print("Oops!", e, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBye!")


if __name__ == "__main__":
    main()
