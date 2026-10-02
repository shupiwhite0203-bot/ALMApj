from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_STARTUP_MESSAGE = (
    "狩猟アシスタントシステムアルマ、起動しました。"
    "できる限りの支援を行います。共に頑張りましょう。"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Start the ALMA Monster Hunter assistant services."
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--checkpoint", type=Path, default=Path("runs/monsters/best.pt"))
    parser.add_argument("--situation-dir", type=Path, default=Path("MonsterHunter_Screenshots/situation"))
    parser.add_argument("--cnn-dir", type=Path, default=Path("MonsterHunter_Screenshots/cnn_train"))
    parser.add_argument("--screenshot", action="store_true", help="Also start periodic screenshot capture.")
    parser.add_argument("--cnn-interval", type=float, default=2.0)
    parser.add_argument("--situation-interval", type=float, default=30.0)
    parser.add_argument("--voicevox", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--detail", choices=["low", "auto", "high"], default="auto")
    parser.add_argument("--process-existing", action="store_true")
    parser.add_argument("--desktop-pet", action="store_true", help="Launch the transparent Electron Live2D companion.")
    parser.add_argument("--electron", type=Path, default=None, help="Path to electron.exe for --desktop-pet.")
    parser.add_argument("--display", type=int, default=1, help="1-based monitor number for --desktop-pet.")
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
    parser.add_argument("--startup-message", default=DEFAULT_STARTUP_MESSAGE)
    parser.add_argument("--no-startup-message", action="store_true")
    return parser.parse_args()


def start_process(name: str, command: list[str]) -> subprocess.Popen:
    print(f"[start] {name}: {' '.join(command)}")
    return subprocess.Popen(command, cwd=ROOT)


def main() -> None:
    args = parse_args()
    processes: list[tuple[str, subprocess.Popen]] = []

    overlay_cmd = [
        args.python,
        "mh_live2d_server.py",
        "--port",
        str(args.port),
        "--no-open",
    ]
    processes.append(("overlay", start_process("overlay", overlay_cmd)))

    if args.desktop_pet:
        pet_cmd = [
            args.python,
            "mh_desktop_companion.py",
            "--url",
            f"http://127.0.0.1:{args.port}/?mode=pet",
            "--display",
            str(args.display),
        ]
        if args.electron:
            pet_cmd.extend(["--electron", str(args.electron)])
        processes.append(("desktop-pet", start_process("desktop-pet", pet_cmd)))

    agent_cmd = [
        args.python,
        "mh_hunt_agent.py",
        "--watch",
        "--situation-dir",
        str(args.situation_dir),
        "--checkpoint",
        str(args.checkpoint),
        "--detail",
        args.detail,
        "--advice-cooldown",
        str(args.advice_cooldown),
        "--same-monster-cooldown",
        str(args.same_monster_cooldown),
        "--confidence-delta",
        str(args.confidence_delta),
        "--min-confidence",
        str(args.min_confidence),
        "--monster-lock-window",
        str(args.monster_lock_window),
        "--frame-burst",
        str(args.frame_burst),
        "--frame-burst-fps",
        str(args.frame_burst_fps),
        "--frame-burst-dir",
        str(args.frame_burst_dir),
        "--knowledge-cache-dir",
        str(args.knowledge_cache_dir),
        "--max-output-tokens",
        str(args.max_output_tokens),
    ]
    if args.hunt_variant:
        agent_cmd.extend(["--hunt-variant", args.hunt_variant])
    if args.no_dynamic_knowledge:
        agent_cmd.append("--no-dynamic-knowledge")
    if args.no_dynamic_knowledge_web:
        agent_cmd.append("--no-dynamic-knowledge-web")
    if args.refresh_knowledge:
        agent_cmd.append("--refresh-knowledge")
    if not args.no_startup_message and args.startup_message:
        agent_cmd.extend(["--startup-message", args.startup_message])
    if args.dry_run:
        agent_cmd.append("--dry-run")
    if args.voicevox:
        agent_cmd.append("--voicevox")
    if args.process_existing:
        agent_cmd.append("--process-existing")
    processes.append(("hunt-agent", start_process("hunt-agent", agent_cmd)))

    if args.screenshot:
        screenshot_cmd = [
            args.python,
            "screenshot.py",
            "--cnn-dir",
            str(args.cnn_dir),
            "--situation-dir",
            str(args.situation_dir),
            "--cnn-interval",
            str(args.cnn_interval),
            "--situation-interval",
            str(args.situation_interval),
        ]
        processes.append(("screenshot", start_process("screenshot", screenshot_cmd)))

    print(f"Overlay URL: http://127.0.0.1:{args.port}/")
    print("Press Ctrl+C to stop all assistant services.")

    try:
        while True:
            for name, process in processes:
                code = process.poll()
                if code is not None:
                    raise RuntimeError(f"{name} exited with code {code}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping assistant services...")
    finally:
        for name, process in processes:
            if process.poll() is None:
                print(f"[stop] {name}")
                process.terminate()
        for _, process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
