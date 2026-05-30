from __future__ import annotations

import argparse
from pathlib import Path

from predict import IMAGE_EXTENSIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show image counts for the Monster Hunter classifier dataset."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data/monsters"))
    return parser.parse_args()


def count_label_images(label_dir: Path) -> int:
    return sum(
        1
        for path in label_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def report(data_dir: Path) -> list[tuple[str, int]]:
    if not data_dir.exists():
        return []
    return [
        (path.name, count_label_images(path))
        for path in sorted(data_dir.iterdir(), key=lambda item: item.name)
        if path.is_dir()
    ]


def main() -> None:
    args = parse_args()
    rows = report(args.data_dir)
    if not rows:
        print(f"No label folders found under: {args.data_dir}")
        return

    total = sum(count for _, count in rows)
    print(f"dataset root: {args.data_dir}")
    print(f"total images: {total}")
    print("labels:")
    for label, count in rows:
        print(f"- {label}: {count}")


if __name__ == "__main__":
    main()
