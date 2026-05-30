from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_LABELS = [
    "レ・ダウ",
    "リオレウス",
    "リオレイア",
    "アルシュベルド",
    "チャタカブラ",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create Monster Hunter classifier dataset folders."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data/monsters"))
    parser.add_argument(
        "--labels",
        nargs="+",
        default=DEFAULT_LABELS,
        help="Class labels. Folder names become classifier labels.",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Create train/val subfolders instead of a single ImageFolder root.",
    )
    return parser.parse_args()


def create_dataset_dirs(data_dir: Path, labels: list[str], split: bool) -> None:
    roots = [data_dir]
    if split:
        roots = [data_dir / "train", data_dir / "val"]

    for root in roots:
        for label in labels:
            (root / label).mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()
    create_dataset_dirs(args.data_dir, args.labels, args.split)

    print(f"dataset root: {args.data_dir}")
    if args.split:
        print("created split layout: train/ and val/")
    print("labels:")
    for label in args.labels:
        print(f"- {label}")


if __name__ == "__main__":
    main()
