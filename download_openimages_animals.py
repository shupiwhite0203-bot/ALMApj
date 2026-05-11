from __future__ import annotations

import shutil
from pathlib import Path

import fiftyone.zoo as foz


CLASSES = {
    "Bird": "鳥",
    "Lion": "ライオン",
    "Dog": "犬",
    "Cat": "猫",
}

SAMPLES_PER_CLASS = 50


def clear_image_files(label_dir: Path) -> None:
    for path in label_dir.iterdir():
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            path.unlink()


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    output_root = project_dir / "data" / "animals"
    output_root.mkdir(parents=True, exist_ok=True)

    for en_label, jp_label in CLASSES.items():
        label_dir = output_root / jp_label
        label_dir.mkdir(parents=True, exist_ok=True)
        clear_image_files(label_dir)

        dataset = foz.load_zoo_dataset(
            "open-images-v7",
            split="validation",
            label_types=["classifications"],
            classes=[en_label],
            only_matching=True,
            max_samples=SAMPLES_PER_CLASS,
            shuffle=True,
            seed=42,
            dataset_name=f"open-images-{en_label.lower()}-{SAMPLES_PER_CLASS}",
        )

        copied = 0
        for sample in dataset:
            src = Path(sample.filepath)
            if not src.exists():
                continue
            dst = label_dir / f"{en_label.lower()}_{copied:04d}{src.suffix.lower()}"
            shutil.copy2(src, dst)
            copied += 1

        print(f"{en_label} -> {jp_label}: {copied} images")


if __name__ == "__main__":
    main()
