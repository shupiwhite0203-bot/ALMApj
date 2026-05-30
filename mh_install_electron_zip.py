from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TARGET_DIR = ROOT / "vendor" / "electron"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install a downloaded Electron zip for ALMA desktop companion.")
    parser.add_argument("zip_path", type=Path, help="Path to an Electron win32-x64 zip file.")
    parser.add_argument("--target", type=Path, default=TARGET_DIR)
    parser.add_argument("--force", action="store_true", help="Replace the existing target directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    zip_path = args.zip_path.expanduser().resolve()
    target = args.target.resolve()

    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    if target.exists():
        if not args.force:
            raise FileExistsError(f"{target} already exists. Use --force to replace it.")
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target)

    electron = target / "electron.exe"
    if not electron.exists():
        raise FileNotFoundError(f"electron.exe was not found after extracting to {target}")

    print(f"Electron installed: {electron}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
