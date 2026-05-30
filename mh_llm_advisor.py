from __future__ import annotations

import argparse
import base64
import os
import time
from datetime import datetime
from pathlib import Path

from predict import IMAGE_EXTENSIONS, predict_image


DEFAULT_MONSTER_CHECKPOINT = Path("runs/monsters/best.pt")
DEFAULT_ANIMAL_CHECKPOINT = Path("runs/animals/best.pt")
DEFAULT_SITUATION_DIR = Path("MonsterHunter_Screenshots/situation")
DEFAULT_LOG_DIR = Path("runs/llm_advice")
DEFAULT_MODEL = "gpt-5.4-mini"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate an image label with a local classifier and ask a multimodal LLM for advice or feedback."
    )
    parser.add_argument("--image", type=Path, help="Screenshot to send. If omitted, the newest situation image is used.")
    parser.add_argument("--situation-dir", type=Path, default=DEFAULT_SITUATION_DIR)
    parser.add_argument("--domain", choices=["monster", "animal"], default="monster")
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--device", default=None)
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--detail", choices=["low", "auto", "high"], default="auto")
    parser.add_argument("--dry-run", action="store_true", help="Show the inferred monster and prompt without calling the API.")
    parser.add_argument("--watch", action="store_true", help="Keep watching the situation folder and process new screenshots.")
    parser.add_argument("--interval", type=float, default=1.0, help="Polling interval in seconds when --watch is used.")
    parser.add_argument("--process-existing", action="store_true", help="When watching, also process screenshots that already exist at startup.")
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR, help="Directory for saved advice logs.")
    return parser.parse_args()


def newest_image(directory: Path) -> Path:
    if not directory.exists():
        raise FileNotFoundError(f"Situation screenshot directory not found: {directory}")

    images = [path for path in directory.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS]
    if not images:
        raise FileNotFoundError(f"No screenshots found under: {directory}")
    return max(images, key=lambda path: path.stat().st_mtime)


def iter_situation_images(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        (path for path in directory.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: path.stat().st_mtime,
    )


def image_data_url(image_path: Path) -> str:
    suffix = image_path.suffix.lower()
    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def wait_for_stable_file(image_path: Path, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    previous_size = -1

    while time.time() < deadline:
        current_size = image_path.stat().st_size
        if current_size > 0 and current_size == previous_size:
            return
        previous_size = current_size
        time.sleep(0.2)


def resolve_checkpoint(domain: str, checkpoint: Path | None) -> Path:
    if checkpoint is not None:
        return checkpoint
    if domain == "animal":
        return DEFAULT_ANIMAL_CHECKPOINT
    return DEFAULT_MONSTER_CHECKPOINT


def build_prompt(predictions: list[tuple[str, float]], domain: str) -> str:
    prediction_lines = "\n".join(
        f"- {name}: {score:.1%}"
        for name, score in predictions
    )
    best_name = predictions[0][0] if predictions else "unknown"

    if domain == "animal":
        return f"""あなたは画像認識テスト用の観察アシスタントです。
画像分類器は、この画像の主な動物を「{best_name}」と推定しました。

推定候補:
{prediction_lines}

画像も確認したうえで、次を日本語で簡潔に答えてください。
1. 推定された動物名と確信度の見立て
2. 画像内でその判断につながる特徴
3. 分類器の推定が間違っていそうな場合の代替候補
4. このパイプラインが正しく動いているかを確認するための短いコメント

分類器の候補と画像内容が食い違う場合は、その不確実性を明記してください。"""

    return f"""あなたはモンスターハンターの狩猟アドバイザーです。
画像分類器は、このスクリーンショットの主なモンスターを「{best_name}」と推定しました。

推定候補:
{prediction_lines}

画像も確認したうえで、次を日本語で簡潔に答えてください。
1. 推定モンスター名と確信度の見立て
2. 弱点属性・有効な状態異常・狙いやすい部位
3. 現在の画面状況から見た立ち回りアドバイス
4. 持ち込みたいアイテムや注意点

ゲーム作品や個体差で弱点が違う可能性がある場合は、その不確実性も明記してください。"""


def request_advice(
    api_key: str,
    model: str,
    image_path: Path,
    prompt: str,
    detail: str,
) -> str:
    try:
        from openai import OpenAI, OpenAIError, RateLimitError
    except ImportError as exc:
        raise RuntimeError("The openai package is not installed. Run: pip install -r requirements.txt") from exc

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": image_data_url(image_path), "detail": detail},
                    ],
                }
            ],
        )
    except RateLimitError as exc:
        message = str(exc)
        if "insufficient_quota" in message:
            raise RuntimeError(
                "OpenAI API quota is insufficient. Add billing/credits to the API project, "
                "or run with --dry-run until API billing is available."
            ) from exc
        raise RuntimeError(f"OpenAI API rate limit error: {exc}") from exc
    except OpenAIError as exc:
        raise RuntimeError(f"OpenAI API request failed: {exc}") from exc

    return response.output_text


def save_log(log_dir: Path, image_path: Path, predictions: list[tuple[str, float]], prompt: str, advice: str) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = log_dir / f"{timestamp}_{image_path.stem}.txt"
    prediction_lines = "\n".join(f"- {name}: {score:.4f}" for name, score in predictions)
    log_path.write_text(
        f"image: {image_path}\n\n"
        f"predictions:\n{prediction_lines}\n\n"
        f"--- prompt ---\n{prompt}\n\n"
        f"--- LLM advice ---\n{advice}\n",
        encoding="utf-8",
    )
    return log_path


def process_image(args: argparse.Namespace, image_path: Path) -> None:
    checkpoint = resolve_checkpoint(args.domain, args.checkpoint)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not checkpoint.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint}")

    predictions = predict_image(image_path, checkpoint, top_k=args.top_k, device_name=args.device)
    prompt = build_prompt(predictions, args.domain)

    print(f"image: {image_path}")
    print(f"domain: {args.domain}")
    print(f"checkpoint: {checkpoint}")
    print("predictions:")
    for name, score in predictions:
        print(f"  {name}: {score:.4f}")

    if args.dry_run:
        print("\n--- prompt ---")
        print(prompt)
        return

    if not args.api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it later, or pass --dry-run to test the local prediction flow."
        )

    advice = request_advice(args.api_key, args.model, image_path, prompt, args.detail)
    print("\n--- LLM advice ---")
    print(advice)

    log_path = save_log(args.log_dir, image_path, predictions, prompt, advice)
    print(f"\nlog: {log_path}")


def watch_situation_folder(args: argparse.Namespace) -> None:
    processed: set[Path] = set()
    if not args.process_existing:
        processed = {path.resolve() for path in iter_situation_images(args.situation_dir)}

    print(f"watching: {args.situation_dir}")
    if processed:
        print(f"already tracked at startup: {len(processed)} screenshots")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            images = iter_situation_images(args.situation_dir)
            new_images = [path for path in images if path.resolve() not in processed]

            for image_path in new_images:
                resolved = image_path.resolve()
                processed.add(resolved)
                print(f"\n=== new screenshot: {image_path} ===")
                try:
                    wait_for_stable_file(image_path)
                    process_image(args, image_path)
                except Exception as exc:
                    print(f"error: {exc}")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nwatch stopped.")


def main() -> None:
    args = parse_args()

    if args.image and args.watch:
        raise ValueError("--image and --watch cannot be used together.")

    if args.watch:
        watch_situation_folder(args)
        return

    image_path = args.image or newest_image(args.situation_dir)
    process_image(args, image_path)


if __name__ == "__main__":
    main()
