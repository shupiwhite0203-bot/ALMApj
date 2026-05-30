from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

import pyautogui


BASE_DIR = Path("MonsterHunter_Screenshots")
CNN_DIR = BASE_DIR / "cnn_train"
SITUATION_DIR = BASE_DIR / "situation"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Periodically capture screenshots for training and hunting situation inference."
    )
    parser.add_argument("--cnn-dir", type=Path, default=CNN_DIR)
    parser.add_argument("--situation-dir", type=Path, default=SITUATION_DIR)
    parser.add_argument("--cnn-interval", type=float, default=2.0)
    parser.add_argument("--situation-interval", type=float, default=30.0)
    parser.add_argument("--prefix", default="")
    return parser.parse_args()


def save_screenshot(directory: Path, prefix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    stem = f"{prefix}_{timestamp}" if prefix else timestamp
    path = directory / f"{stem}.png"
    pyautogui.screenshot().save(path)
    return path


def main() -> None:
    args = parse_args()
    args.cnn_dir.mkdir(parents=True, exist_ok=True)
    args.situation_dir.mkdir(parents=True, exist_ok=True)

    last_cnn = 0.0
    last_situation = 0.0

    print("Screenshot capture started. Press Ctrl+C to stop.")
    print(f"training data: {args.cnn_dir}")
    print(f"situation data: {args.situation_dir}")

    try:
        while True:
            now = time.time()

            if args.cnn_interval > 0 and now - last_cnn >= args.cnn_interval:
                path = save_screenshot(args.cnn_dir, args.prefix)
                print(f"[cnn] saved: {path}")
                last_cnn = now

            if args.situation_interval > 0 and now - last_situation >= args.situation_interval:
                path = save_screenshot(args.situation_dir, args.prefix)
                print(f"[situation] saved: {path}")
                last_situation = now

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Screenshot capture stopped.")


if __name__ == "__main__":
    main()
