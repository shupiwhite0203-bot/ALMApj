from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import torch
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms
from tqdm import tqdm


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train an EfficientNet-B0 image classifier.")
    parser.add_argument("--data-dir", type=Path, required=True, help="ImageFolder root directory.")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/efficientnet_b0"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pretrained", action="store_true", help="Use ImageNet pretrained weights.")
    parser.add_argument("--freeze-backbone", action="store_true", help="Train only classifier head.")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


def build_transforms(image_size: int) -> tuple[transforms.Compose, transforms.Compose]:
    train_tfms = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(8),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.12),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    eval_tfms = transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )
    return train_tfms, eval_tfms


def has_split_dirs(data_dir: Path) -> bool:
    return (data_dir / "train").is_dir() and (data_dir / "val").is_dir()


def count_images(data_dir: Path) -> int:
    return sum(1 for path in data_dir.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS)


def build_datasets(data_dir: Path, image_size: int, val_split: float, seed: int):
    train_tfms, eval_tfms = build_transforms(image_size)

    if has_split_dirs(data_dir):
        train_ds = datasets.ImageFolder(data_dir / "train", transform=train_tfms)
        val_ds = datasets.ImageFolder(data_dir / "val", transform=eval_tfms)
        if train_ds.classes != val_ds.classes:
            raise ValueError("train and val folders must contain the same class names.")
        return train_ds, val_ds, train_ds.classes

    full_train = datasets.ImageFolder(data_dir, transform=train_tfms)
    full_eval = datasets.ImageFolder(data_dir, transform=eval_tfms)
    if len(full_train.classes) < 2:
        raise ValueError("At least two class folders are required.")

    val_size = max(1, int(len(full_train) * val_split))
    train_size = len(full_train) - val_size
    if train_size < 1:
        raise ValueError("Not enough images for train/validation split.")

    generator = torch.Generator().manual_seed(seed)
    indices = torch.randperm(len(full_train), generator=generator).tolist()
    train_indices = indices[:train_size]
    val_indices = indices[train_size:]
    return Subset(full_train, train_indices), Subset(full_eval, val_indices), full_train.classes


def build_model(num_classes: int, pretrained: bool, freeze_backbone: bool) -> nn.Module:
    weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None
    model = models.efficientnet_b0(weights=weights)

    if freeze_backbone:
        for parameter in model.features.parameters():
            parameter.requires_grad = False

    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
) -> tuple[float, float]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_correct = 0
    total_items = 0

    context = torch.enable_grad() if training else torch.no_grad()
    with context:
        for images, labels in tqdm(loader, leave=False):
            images = images.to(device)
            labels = labels.to(device)

            if training:
                optimizer.zero_grad(set_to_none=True)

            logits = model(images)
            loss = criterion(logits, labels)

            if training:
                loss.backward()
                optimizer.step()

            batch_size = labels.size(0)
            total_loss += loss.item() * batch_size
            total_correct += (logits.argmax(dim=1) == labels).sum().item()
            total_items += batch_size

    return total_loss / total_items, total_correct / total_items


def save_checkpoint(
    path: Path,
    model: nn.Module,
    class_names: list[str],
    image_size: int,
    epoch: int,
    val_acc: float,
) -> None:
    checkpoint = {
        "model_name": "efficientnet_b0",
        "state_dict": model.state_dict(),
        "class_names": class_names,
        "image_size": image_size,
        "epoch": epoch,
        "val_acc": val_acc,
    }
    torch.save(checkpoint, path)


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if not args.data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {args.data_dir}")
    if count_images(args.data_dir) == 0:
        raise ValueError(f"No images found under: {args.data_dir}")

    train_ds, val_ds, class_names = build_datasets(args.data_dir, args.image_size, args.val_split, args.seed)
    device = torch.device(args.device)

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=device.type == "cuda",
    )

    model = build_model(len(class_names), args.pretrained, args.freeze_backbone).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(
        (p for p in model.parameters() if p.requires_grad),
        lr=args.lr,
        weight_decay=args.weight_decay,
    )

    metadata_path = args.output_dir / "classes.json"
    metadata_path.write_text(json.dumps(class_names, ensure_ascii=False, indent=2), encoding="utf-8")

    best_acc = 0.0
    start = perf_counter()
    print(f"classes: {class_names}")
    print(f"device: {device}")

    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = run_epoch(model, train_loader, criterion, device, optimizer)
        val_loss, val_acc = run_epoch(model, val_loader, criterion, device)

        print(
            f"epoch {epoch:03d}/{args.epochs:03d} "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f}"
        )

        save_checkpoint(args.output_dir / "last.pt", model, class_names, args.image_size, epoch, val_acc)
        if val_acc >= best_acc:
            best_acc = val_acc
            save_checkpoint(args.output_dir / "best.pt", model, class_names, args.image_size, epoch, val_acc)

    elapsed = perf_counter() - start
    print(f"done: best_val_acc={best_acc:.4f} elapsed_sec={elapsed:.1f}")
    print(f"best checkpoint: {args.output_dir / 'best.pt'}")


if __name__ == "__main__":
    main()
