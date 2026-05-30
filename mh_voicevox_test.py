from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from mh_assistant.voicevox import VoicevoxClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test VOICEVOX synthesis for ALMA.")
    parser.add_argument("--url", default="http://127.0.0.1:50021")
    parser.add_argument("--speaker", type=int, default=47)
    parser.add_argument("--text", default="音声テストです。狩猟支援を開始します。")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/voicevox"))
    parser.add_argument("--list", action="store_true", help="Print matching speakers/styles and exit.")
    return parser.parse_args()


def list_speakers(client: VoicevoxClient, target_speaker: int) -> None:
    for speaker in client.speakers():
        for style in speaker.get("styles", []):
            style_id = int(style.get("id", -1))
            if style_id == target_speaker or "ナースロボ" in speaker.get("name", ""):
                print(f"{speaker.get('name')} | {style.get('name')} | {style_id}")


def main() -> None:
    args = parse_args()
    client = VoicevoxClient(
        base_url=args.url,
        speaker=args.speaker,
        output_dir=args.output_dir,
    )

    if args.list:
        list_speakers(client, args.speaker)
        return

    client.assert_available()
    file_stem = f"voicevox_test_{datetime.now():%Y%m%d_%H%M%S}"
    output_path = client.synthesize(args.text, file_stem)
    print(output_path)


if __name__ == "__main__":
    main()
