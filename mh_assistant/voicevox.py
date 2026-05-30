from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class VoicevoxClient:
    """Small VOICEVOX Engine client.

    VOICEVOX Engine must be running separately.
    The speaker id is configurable because voice/style ids can differ by install.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:50021",
        speaker: int = 47,
        output_dir: Path = Path("runs/voicevox"),
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.speaker = speaker
        self.output_dir = output_dir

    def speakers(self) -> list[dict[str, Any]]:
        request = urllib.request.Request(f"{self.base_url}/speakers", method="GET")
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def assert_available(self) -> None:
        self.speakers()

    def synthesize(self, text: str, file_stem: str) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        query = self._audio_query(text)
        audio = self._synthesis(query)
        output_path = self.output_dir / f"{file_stem}.wav"
        output_path.write_bytes(audio)
        return output_path

    def _audio_query(self, text: str) -> dict:
        params = urllib.parse.urlencode({"text": text, "speaker": self.speaker})
        request = urllib.request.Request(
            f"{self.base_url}/audio_query?{params}",
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def _synthesis(self, query: dict) -> bytes:
        params = urllib.parse.urlencode({"speaker": self.speaker})
        body = json.dumps(query, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/synthesis?{params}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
