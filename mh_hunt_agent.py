from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import pyautogui

from mh_llm_advisor import (
    DEFAULT_MODEL,
    DEFAULT_MONSTER_CHECKPOINT,
    DEFAULT_SITUATION_DIR,
    iter_situation_images,
    newest_image,
    wait_for_stable_file,
)
from mh_assistant.pipeline import MonsterHunterAssistantPipeline
from mh_assistant.voicevox import VoicevoxClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Monster Hunter desktop assistant pipeline."
    )
    parser.add_argument("--image", type=Path)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--process-existing", action="store_true")
    parser.add_argument("--situation-dir", type=Path, default=DEFAULT_SITUATION_DIR)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_MONSTER_CHECKPOINT)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--device", default=None)
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--detail", choices=["low", "auto", "high"], default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--voicevox", action="store_true")
    parser.add_argument("--voicevox-url", default=os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021"))
    parser.add_argument("--voicevox-speaker", type=int, default=int(os.getenv("VOICEVOX_SPEAKER", "47")))
    parser.add_argument("--live2d-event", type=Path, default=Path("runs/live2d/latest_event.json"))
    parser.add_argument("--advice-cooldown", type=float, default=30.0)
    parser.add_argument("--same-monster-cooldown", type=float, default=0.0)
    parser.add_argument("--confidence-delta", type=float, default=0.15)
    parser.add_argument("--min-confidence", type=float, default=0.0)
    parser.add_argument("--monster-lock-window", type=float, default=90.0)
    parser.add_argument("--frame-burst", type=int, default=1)
    parser.add_argument("--frame-burst-fps", type=float, default=3.0)
    parser.add_argument("--frame-burst-dir", type=Path, default=Path("MonsterHunter_Screenshots/situation_burst"))
    parser.add_argument("--hunt-variant", default=None, help="Optional hunt variant, for example: 歴戦王")
    parser.add_argument("--knowledge-cache-dir", type=Path, default=Path("knowledge_cache"))
    parser.add_argument("--no-dynamic-knowledge", action="store_true")
    parser.add_argument("--no-dynamic-knowledge-web", action="store_true")
    parser.add_argument("--refresh-knowledge", action="store_true")
    parser.add_argument("--max-output-tokens", type=int, default=150)
    parser.add_argument("--startup-message", default=None)
    return parser.parse_args()


def build_pipeline(args: argparse.Namespace) -> MonsterHunterAssistantPipeline:
    voicevox = None
    if args.voicevox:
        voicevox = VoicevoxClient(
            base_url=args.voicevox_url,
            speaker=args.voicevox_speaker,
        )

    return MonsterHunterAssistantPipeline(
        checkpoint=args.checkpoint,
        model=args.model,
        api_key=args.api_key,
        detail=args.detail,
        device=args.device,
        top_k=args.top_k,
        dry_run=args.dry_run,
        voicevox=voicevox,
        live2d_event_path=args.live2d_event,
        advice_cooldown_seconds=args.advice_cooldown,
        same_monster_cooldown_seconds=args.same_monster_cooldown,
        confidence_delta_threshold=args.confidence_delta,
        min_confidence=args.min_confidence,
        monster_lock_window_seconds=args.monster_lock_window,
        hunt_variant=args.hunt_variant,
        dynamic_knowledge=not args.no_dynamic_knowledge,
        dynamic_knowledge_web=not args.no_dynamic_knowledge_web,
        knowledge_cache_dir=args.knowledge_cache_dir,
        refresh_knowledge=args.refresh_knowledge,
        max_output_tokens=args.max_output_tokens,
    )


def print_result(result) -> None:
    event = result.event
    print(f"hunt_id: {event['hunt_id']}")
    print(f"turn: {event['turn_count']}")
    print(f"monster: {event['predicted_monster']} ({event['confidence']:.1%})")
    if result.suppressed:
        print(f"suppressed: {result.suppress_reason}")
        return
    print(f"advice: {result.advice}")
    if result.audio_path:
        print(f"voicevox: {result.audio_path}")
    if result.live2d_event_path:
        print(f"live2d_event: {result.live2d_event_path}")


def capture_burst_frames(first_image: Path, args: argparse.Namespace) -> list[Path]:
    frame_count = max(1, args.frame_burst)
    if frame_count <= 1:
        return [first_image]

    interval = 1.0 / max(0.1, args.frame_burst_fps)
    args.frame_burst_dir.mkdir(parents=True, exist_ok=True)
    frames = [first_image]
    burst_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    for index in range(2, frame_count + 1):
        time.sleep(interval)
        path = args.frame_burst_dir / f"{burst_id}_f{index:02d}.png"
        pyautogui.screenshot().save(path)
        frames.append(path)

    return frames


def run_once(args: argparse.Namespace) -> None:
    pipeline = build_pipeline(args)
    if args.startup_message:
        print_result(pipeline.emit_message(args.startup_message, expression="joy"))
    image_path = args.image or newest_image(args.situation_dir)
    image_paths = capture_burst_frames(image_path, args)
    result = pipeline.process_images(image_paths)
    print_result(result)


def run_watch(args: argparse.Namespace) -> None:
    pipeline = build_pipeline(args)
    if args.startup_message:
        print_result(pipeline.emit_message(args.startup_message, expression="joy"))

    processed: set[Path] = set()
    if not args.process_existing:
        processed = {path.resolve() for path in iter_situation_images(args.situation_dir)}

    print(f"watching: {args.situation_dir}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            for image_path in iter_situation_images(args.situation_dir):
                resolved = image_path.resolve()
                if resolved in processed:
                    continue
                processed.add(resolved)
                wait_for_stable_file(image_path)
                try:
                    image_paths = capture_burst_frames(image_path, args)
                    result = pipeline.process_images(image_paths)
                    print_result(result)
                except Exception as exc:
                    print(f"error: {exc}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("watch stopped.")


def main() -> None:
    args = parse_args()
    if args.image and args.watch:
        raise ValueError("--image and --watch cannot be used together.")
    if args.watch:
        run_watch(args)
    else:
        run_once(args)


if __name__ == "__main__":
    main()
