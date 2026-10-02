from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from time import perf_counter

import torch
import torchvision
from torchvision.datasets import ImageFolder

from predict import build_transform, load_checkpoint_model


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a local classifier on explicitly supplied labeled images.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads must be positive")
    torch.set_num_threads(args.threads)
    device = torch.device(args.device)
    model, classes, size = load_checkpoint_model(args.checkpoint, device)
    dataset = ImageFolder(args.data_dir, transform=build_transform(size))
    if dataset.classes != classes:
        raise ValueError("Dataset classes must exactly match checkpoint classes.")
    confusion = [[0 for _ in classes] for _ in classes]
    inference_ms = []
    frame_ms = []

    def synchronize() -> None:
        if device.type == "cuda":
            torch.cuda.synchronize(device)

    with torch.inference_mode():
        # Warm up before timing; checkpoint loading is excluded.
        model(dataset[0][0].unsqueeze(0).to(device))
        synchronize()
        for index in range(len(dataset)):
            frame_start = perf_counter()
            image, label = dataset[index]
            batch = image.unsqueeze(0).to(device)
            synchronize()
            inference_start = perf_counter()
            prediction = model(batch).argmax(dim=1).item()
            synchronize()
            end = perf_counter()
            inference_ms.append((end - inference_start) * 1000)
            frame_ms.append((end - frame_start) * 1000)
            confusion[label][prediction] += 1

    total = len(dataset)
    per_class = []
    for i, name in enumerate(classes):
        support = sum(confusion[i])
        tp = confusion[i][i]
        predicted = sum(row[i] for row in confusion)
        precision = tp / predicted if predicted else 0.0
        recall = tp / support if support else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class.append(dict(label=name, images=support, precision=precision, recall=recall, f1=f1))

    report = {
        "scope": "Supplied dataset only; independence from training data is NOT verified.",
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "images": total,
        "classes": classes,
        "accuracy": sum(confusion[i][i] for i in range(len(classes))) / total,
        "macro_f1": sum(row["f1"] for row in per_class) / len(classes),
        "per_class": per_class,
        "confusion_matrix": confusion,
        "matrix_axes": "rows=true labels, columns=predicted labels, in classes order",
        "inference_ms": dict(p50=percentile(inference_ms, 0.5), p95=percentile(inference_ms, 0.95)),
        "image_to_prediction_ms": dict(p50=percentile(frame_ms, 0.5), p95=percentile(frame_ms, 0.95)),
        "timing_scope": "Batch size 1, warmed-up model. Includes image loading/transform for image_to_prediction; excludes screenshot, model loading and API.",
        "environment": dict(python=platform.python_version(), torch=torch.__version__,
                            torchvision=torchvision.__version__, device=str(device), threads=args.threads,
                            platform=platform.system(), machine=platform.machine()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"images={total} accuracy={report['accuracy']:.4f} macro_f1={report['macro_f1']:.4f}")
    print(f"report: {args.output}")


if __name__ == "__main__":
    main()
