from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = Path(r"C:\Users\spieler\AppData\Local\Programs\open-llm-vtuber")
TARGET_DIR = ROOT / "vendor" / "electron"
COMPANION_DIR = ROOT / "desktop_companion"


SKIP_ROOT_NAMES = {
    "Uninstall open-llm-vtuber-electron.exe",
}

SKIP_RESOURCE_NAMES = {
    "app.asar",
    "app.asar.unpacked",
    "app-update.yml",
    "elevate.exe",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an ALMA Electron shell from an installed Open-LLM-VTuber Electron app."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--target", type=Path, default=TARGET_DIR)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def copy_item(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main() -> None:
    args = parse_args()
    source = args.source.resolve()
    target = args.target.resolve()

    exe = source / "open-llm-vtuber-electron.exe"
    if not exe.exists():
        raise FileNotFoundError(f"Open-LLM-VTuber Electron executable not found: {exe}")
    if not COMPANION_DIR.exists():
        raise FileNotFoundError(f"desktop_companion not found: {COMPANION_DIR}")
    if target.exists():
        if not args.force:
            raise FileExistsError(f"{target} already exists. Use --force to replace it.")
        shutil.rmtree(target)

    target.mkdir(parents=True)

    for item in source.iterdir():
        if item.name in SKIP_ROOT_NAMES:
            continue
        if item.name == "resources":
            resources_target = target / "resources"
            resources_target.mkdir(parents=True, exist_ok=True)
            for resource in item.iterdir():
                if resource.name in SKIP_RESOURCE_NAMES:
                    continue
                copy_item(resource, resources_target / resource.name)
            continue
        copy_item(item, target / item.name)

    app_target = target / "resources" / "app"
    app_target.mkdir(parents=True, exist_ok=True)
    for name in ("main.js", "preload.js", "package.json"):
        shutil.copy2(COMPANION_DIR / name, app_target / name)

    if not (target / "open-llm-vtuber-electron.exe").exists():
        raise FileNotFoundError("Failed to copy open-llm-vtuber-electron.exe")
    if not (app_target / "main.js").exists():
        raise FileNotFoundError("Failed to install ALMA desktop companion app")

    print(f"ALMA Electron shell installed: {target}")
    print(f"Executable: {target / 'open-llm-vtuber-electron.exe'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
