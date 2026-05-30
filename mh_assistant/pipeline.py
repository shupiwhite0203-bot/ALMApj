from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import time

from mh_llm_advisor import request_advice
from predict import predict_image

from .live2d_event import write_live2d_event
from .monster_knowledge import get_monster_knowledge
from .prompts import build_hunt_advice_prompt
from .session import HuntSession, Prediction
from .voicevox import VoicevoxClient


@dataclass
class PipelineResult:
    event: dict
    prompt: str
    advice: str
    audio_path: Path | None
    live2d_event_path: Path | None
    suppressed: bool = False
    suppress_reason: str | None = None


class MonsterHunterAssistantPipeline:
    def __init__(
        self,
        checkpoint: Path,
        model: str,
        api_key: str | None,
        detail: str = "auto",
        device: str | None = None,
        top_k: int = 3,
        dry_run: bool = False,
        voicevox: VoicevoxClient | None = None,
        live2d_event_path: Path | None = Path("runs/live2d/latest_event.json"),
        advice_cooldown_seconds: float = 30.0,
        same_monster_cooldown_seconds: float = 0.0,
        confidence_delta_threshold: float = 0.15,
        min_confidence: float = 0.35,
    ) -> None:
        self.checkpoint = checkpoint
        self.model = model
        self.api_key = api_key
        self.detail = detail
        self.device = device
        self.top_k = top_k
        self.dry_run = dry_run
        self.voicevox = voicevox
        self.live2d_event_path = live2d_event_path
        self.advice_cooldown_seconds = advice_cooldown_seconds
        self.same_monster_cooldown_seconds = same_monster_cooldown_seconds
        self.confidence_delta_threshold = confidence_delta_threshold
        self.min_confidence = min_confidence
        self.session = HuntSession()
        self._last_advice_at: float | None = None
        self._last_advice_monster: str | None = None
        self._last_advice_confidence: float | None = None

    def process_image(self, image_path: Path) -> PipelineResult:
        raw_predictions = predict_image(
            image_path,
            self.checkpoint,
            top_k=self.top_k,
            device_name=self.device,
        )
        predictions = [
            Prediction(label=label, confidence=confidence)
            for label, confidence in raw_predictions
        ]
        event = self.session.next_turn(image_path=image_path, predictions=predictions)
        prompt = build_hunt_advice_prompt(event)
        suppress_reason = self._suppression_reason(event)

        if suppress_reason:
            return PipelineResult(
                event=event,
                prompt=prompt,
                advice="",
                audio_path=None,
                live2d_event_path=None,
                suppressed=True,
                suppress_reason=suppress_reason,
            )

        if self.dry_run:
            advice = self._dry_run_advice(event)
        else:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is not set. Use --dry-run for local testing.")
            advice = request_advice(
                api_key=self.api_key,
                model=self.model,
                image_path=image_path,
                prompt=prompt,
                detail=self.detail,
            )

        audio_path = None
        if self.voicevox and advice.strip():
            file_stem = f"{datetime.now():%Y%m%d_%H%M%S}_{image_path.stem}"
            audio_path = self.voicevox.synthesize(advice, file_stem)

        if self.live2d_event_path:
            write_live2d_event(
                event_path=self.live2d_event_path,
                text=advice,
                audio_path=audio_path,
                expression=self._expression_for_event(event),
                metadata=event,
            )

        if advice.strip():
            self._record_advice(event)

        return PipelineResult(
            event=event,
            prompt=prompt,
            advice=advice,
            audio_path=audio_path,
            live2d_event_path=self.live2d_event_path,
        )

    def _suppression_reason(self, event: dict) -> str | None:
        if event["is_first_advice"]:
            return None

        monster = event["predicted_monster"]
        confidence = float(event["confidence"])
        now = time.monotonic()

        if confidence < self.min_confidence and self._last_advice_at is not None:
            return f"confidence {confidence:.0%} is below minimum {self.min_confidence:.0%}"

        if self._last_advice_at is None:
            return None

        elapsed = now - self._last_advice_at
        if elapsed < self.advice_cooldown_seconds:
            return f"global cooldown {elapsed:.1f}s/{self.advice_cooldown_seconds:.1f}s"

        if self.same_monster_cooldown_seconds > 0 and monster == self._last_advice_monster:
            last_confidence = self._last_advice_confidence or 0.0
            confidence_delta = abs(confidence - last_confidence)
            if (
                elapsed < self.same_monster_cooldown_seconds
                and confidence_delta < self.confidence_delta_threshold
            ):
                return (
                    f"same monster cooldown {elapsed:.1f}s/"
                    f"{self.same_monster_cooldown_seconds:.1f}s"
                )

        return None

    def _record_advice(self, event: dict) -> None:
        self._last_advice_at = time.monotonic()
        self._last_advice_monster = event["predicted_monster"]
        self._last_advice_confidence = float(event["confidence"])

    @staticmethod
    def _dry_run_advice(event: dict) -> str:
        monster = event["predicted_monster"]
        confidence = float(event["confidence"])
        knowledge = get_monster_knowledge(monster)

        if event["is_first_advice"]:
            if knowledge:
                return (
                    f"推定では{monster}です。{knowledge.features} "
                    f"弱点属性は、{knowledge.weakness}"
                )
            return f"推定では{monster}です。特徴と弱点属性は、本番LLM接続時にここで短く案内します。"

        if knowledge:
            return (
                f"{monster}の推定信頼度は{confidence:.0%}です。"
                f"{knowledge.notes or '無理せず攻撃後の隙を狙いましょう。'}"
            )
        return f"{monster}の推定信頼度は{confidence:.0%}です。無理せず距離を取り、攻撃後の隙を狙いましょう。"

    @staticmethod
    def _expression_for_event(event: dict) -> str:
        confidence = float(event["confidence"])
        if confidence < 0.5:
            return "surprised"
        if event["is_first_advice"]:
            return "joy"
        return "neutral"
