from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class Prediction:
    label: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "confidence": self.confidence}


@dataclass
class HuntSession:
    hunt_id: str = field(
        default_factory=lambda: f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}"
    )
    first_advice_sent: bool = False
    last_monster: str | None = None
    turn_count: int = 0
    started_at: datetime = field(default_factory=datetime.now)

    def next_turn(
        self,
        image_path: Path,
        predictions: list[Prediction],
    ) -> dict[str, Any]:
        self.turn_count += 1
        best = predictions[0] if predictions else None
        if best:
            self.last_monster = best.label

        event = {
            "hunt_id": self.hunt_id,
            "turn_count": self.turn_count,
            "is_first_advice": not self.first_advice_sent,
            "image_path": str(image_path),
            "predicted_monster": best.label if best else "unknown",
            "confidence": best.confidence if best else 0.0,
            "top_candidates": [prediction.to_dict() for prediction in predictions],
            "elapsed_seconds": int((datetime.now() - self.started_at).total_seconds()),
        }

        self.first_advice_sent = True
        return event

