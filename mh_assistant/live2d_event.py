from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_live2d_event(
    event_path: Path,
    text: str,
    audio_path: Path | None,
    expression: str = "neutral",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write a simple event file for a future Live2D desktop layer.

    This is intentionally small: the final renderer can watch this JSON and
    decide how to play audio, update subtitles, and switch expressions.
    """

    event_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "hunt-advice",
        "text": text,
        "audio_path": str(audio_path) if audio_path else None,
        "expression": expression,
        "metadata": metadata or {},
    }
    event_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

