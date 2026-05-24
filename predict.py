from __future__ import annotations

import argparse
from pathlib import Path

import torch
from PIL import Image
from torchvision import models, transforms


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict image labels with a trained EfficientNet-B0 model.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True, help="Image file or directory.")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def build_transform(image_size: int) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )


def build_model(num_classes: int) -> torch.nn.Module:
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = torch.nn.Linear(in_features, num_classes)
    return model


def iter_images(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)
    raise FileNotFoundError(f"Image path not found: {path}")


def load_image(path: Path, transform: transforms.Compose) -> torch.Tensor:
    with Image.open(path) as image:
        image = image.convert("RGB")
        return transform(image).unsqueeze(0)


def load_checkpoint_model(checkpoint_path: Path, device: torch.device) -> tuple[torch.nn.Module, list[str], int]:
    checkpoint = torch.load(checkpoint_path, map_location=device)
    class_names: list[str] = checkpoint["class_names"]
    image_size = int(checkpoint.get("image_size", 224))

    model = build_model(len(class_names)).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model, class_names, image_size


def predict_image(
    image_path: Path,
    checkpoint_path: Path,
    top_k: int = 3,
    device_name: str | None = None,
) -> list[tuple[str, float]]:
    device = torch.device(device_name or ("cuda" if torch.cuda.is_available() else "cpu"))
    model, class_names, image_size = load_checkpoint_model(checkpoint_path, device)
    top_k = min(top_k, len(class_names))
    transform = build_transform(image_size)

    with torch.no_grad():
        batch = load_image(image_path, transform).to(device)
        probabilities = torch.softmax(model(batch), dim=1)[0]
        values, indices = torch.topk(probabilities, k=top_k)

    return [
        (class_names[index.item()], value.item())
        for value, index in zip(values, indices)
    ]


def main() -> None:
    args = parse_args()
    device = torch.device(args.device)

    model, class_names, image_size = load_checkpoint_model(args.checkpoint, device)
    top_k = min(args.top_k, len(class_names))

    transform = build_transform(image_size)
    images = iter_images(args.image)
    if not images:
        raise ValueError(f"No images found under: {args.image}")

    with torch.no_grad():
        for image_path in images:
            batch = load_image(image_path, transform).to(device)
            probabilities = torch.softmax(model(batch), dim=1)[0]
            values, indices = torch.topk(probabilities, k=top_k)

            predictions = [
                f"{class_names[index.item()]}={value.item():.4f}"
                for value, index in zip(values, indices)
            ]
            print(f"{image_path}: {', '.join(predictions)}")


if __name__ == "__main__":
    main()
