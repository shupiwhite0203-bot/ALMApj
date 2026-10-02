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
    locked_monster: str | None = None
    turn_count: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    prediction_history: list[tuple[str, float]] = field(default_factory=list)

    def next_turn(
        self,
        image_path: Path,
        predictions: list[Prediction],
        monster_lock_window_seconds: float = 90.0,
    ) -> dict[str, Any]:
        self.turn_count += 1
        best = predictions[0] if predictions else None
        if best:
            self.last_monster = best.label
            self.prediction_history.append((best.label, best.confidence))

        elapsed_seconds = int((datetime.now() - self.started_at).total_seconds())
        if (
            self.locked_monster is None
            and monster_lock_window_seconds > 0
            and elapsed_seconds >= monster_lock_window_seconds
            and self.prediction_history
        ):
            self.locked_monster = self._choose_locked_monster()

        predicted_monster = self.locked_monster or (best.label if best else "unknown")
        confidence = best.confidence if best else 0.0

        first_advice_due = not self.first_advice_sent and (
            self.locked_monster is not None or monster_lock_window_seconds <= 0
        )

        event = {
            "hunt_id": self.hunt_id,
            "turn_count": self.turn_count,
            "is_first_advice": first_advice_due,
            "image_path": str(image_path),
            "predicted_monster": predicted_monster,
            "confidence": confidence,
            "raw_predicted_monster": best.label if best else "unknown",
            "raw_confidence": confidence,
            "locked_monster": self.locked_monster,
            "monster_locked": self.locked_monster is not None,
            "monster_lock_window_seconds": monster_lock_window_seconds,
            "top_candidates": [prediction.to_dict() for prediction in predictions],
            "elapsed_seconds": elapsed_seconds,
        }

        if first_advice_due:
            self.first_advice_sent = True
        return event

    def _choose_locked_monster(self) -> str:
        scores: dict[str, float] = {}
        counts: dict[str, int] = {}
        for label, confidence in self.prediction_history:
            scores[label] = scores.get(label, 0.0) + confidence
            counts[label] = counts.get(label, 0) + 1

        return max(
            scores,
            key=lambda label: (counts[label], scores[label], label),
        )
