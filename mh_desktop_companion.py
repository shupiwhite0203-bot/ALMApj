from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMPANION_DIR = ROOT / "desktop_companion"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the ALMA Live2D desktop pet companion.")
    parser.add_argument("--url", default="http://127.0.0.1:18080/?mode=pet")
    parser.add_argument("--display", type=int, default=1, help="1-based monitor number for the transparent pet window.")
    parser.add_argument(
        "--electron",
        type=Path,
        default=Path(os.environ["ALMA_ELECTRON_EXE"]) if os.environ.get("ALMA_ELECTRON_EXE") else None,
        help="Path to electron.exe. You can also set ALMA_ELECTRON_EXE.",
    )
    return parser.parse_args()


def find_electron(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit)
    candidates.extend(
        [
            COMPANION_DIR / "node_modules" / ".bin" / "electron.cmd",
            COMPANION_DIR / "node_modules" / "electron" / "dist" / "electron.exe",
            ROOT / "vendor" / "electron" / "electron.exe",
            ROOT / "vendor" / "electron" / "open-llm-vtuber-electron.exe",
            ROOT / "vendor" / "electron" / "electron-v31.7.7-win32-x64" / "electron.exe",
        ]
    )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Electron executable was not found. Install dependencies in desktop_companion, "
        "or place electron.exe under vendor/electron, or set ALMA_ELECTRON_EXE."
    )


def build_command(electron: Path, url: str, display: int) -> list[str]:
    packaged_app = electron.parent / "resources" / "app" / "package.json"
    if packaged_app.exists():
        return [str(electron), f"--url={url}", f"--display={display}"]
    return [str(electron), str(COMPANION_DIR), f"--url={url}", f"--display={display}"]


def main() -> None:
    args = parse_args()
    electron = find_electron(args.electron)
    command = build_command(electron, args.url, args.display)
    print("[desktop-companion]", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)
