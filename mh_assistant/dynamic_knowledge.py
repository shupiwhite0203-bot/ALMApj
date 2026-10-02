from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re


@dataclass(frozen=True)
class DynamicKnowledge:
    target_name: str
    summary: str
    sources: list[str]
    cached: bool
    cache_path: Path | None = None


def build_knowledge_target(monster_name: str, hunt_variant: str | None = None) -> str:
    variant = (hunt_variant or "").strip()
    monster = monster_name.strip()
    if not variant:
        return monster
    if variant in monster:
        return monster
    return f"{variant} {monster}"


def compact_summary_for_prompt(summary: str, max_chars: int = 520) -> str:
    text = strip_prompt_noise(summary)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip("。、 \n") + "。"


def extract_tactical_keywords(summary: str) -> list[str]:
    text = strip_prompt_noise(summary)
    candidates = [
        "鎖刃翼",
        "片翼解除",
        "両翼解除",
        "大ダウン",
        "強化状態",
        "攻撃範囲",
        "連撃",
        "閃光弾",
        "龍属性",
        "龍武器",
        "鎖刃解放",
        "竜属性やられ",
        "歴戦傷",
        "傷",
        "竜乳結晶",
        "属性スリンガー",
        "攻撃力",
        "会心",
        "正面",
        "側面",
    ]

    found: list[str] = []
    for keyword in candidates:
        if keyword in text and keyword not in found:
            found.append(keyword)
    return found[:12]


def strip_prompt_noise(summary: str) -> str:
    text = summary.strip()
    text = re.sub(r"\s*\(\[[^\]]+\]\([^)]+\)\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


class DynamicKnowledgeProvider:
    def __init__(
        self,
        cache_dir: Path = Path("knowledge_cache"),
        enabled: bool = True,
        allow_web: bool = True,
    ) -> None:
        self.cache_dir = cache_dir
        self.enabled = enabled
        self.allow_web = allow_web

    def get(
        self,
        target_name: str,
        api_key: str | None,
        model: str,
        force_refresh: bool = False,
    ) -> DynamicKnowledge | None:
        if not self.enabled:
            return None

        cache_path = self._cache_path(target_name)
        if not force_refresh:
            cached = self._read_cache(cache_path)
            if cached:
                return cached

        if not self.allow_web or not api_key:
            return None

        try:
            knowledge = self._fetch_with_openai_web_search(
                target_name=target_name,
                api_key=api_key,
                model=model,
            )
        except Exception as exc:
            print(f"dynamic knowledge fetch failed for {target_name}: {exc}")
            return None

        self._write_cache(cache_path, knowledge)
        return DynamicKnowledge(
            target_name=knowledge.target_name,
            summary=knowledge.summary,
            sources=knowledge.sources,
            cached=False,
            cache_path=cache_path,
        )

    def _cache_path(self, target_name: str) -> Path:
        digest = hashlib.sha1(target_name.encode("utf-8")).hexdigest()[:12]
        safe_name = re.sub(r'[\\/:*?"<>|\s]+', "_", target_name).strip("_")
        safe_name = safe_name or "monster"
        return self.cache_dir / f"{safe_name}_{digest}.json"

    @staticmethod
    def _read_cache(cache_path: Path) -> DynamicKnowledge | None:
        if not cache_path.exists():
            return None
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        summary = str(data.get("summary") or "").strip()
        target_name = str(data.get("target_name") or "").strip()
        if not summary or not target_name:
            return None

        sources = data.get("sources")
        if not isinstance(sources, list):
            sources = []
        return DynamicKnowledge(
            target_name=target_name,
            summary=summary,
            sources=[str(source) for source in sources],
            cached=True,
            cache_path=cache_path,
        )

    @staticmethod
    def _write_cache(cache_path: Path, knowledge: DynamicKnowledge) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "target_name": knowledge.target_name,
            "summary": knowledge.summary,
            "sources": knowledge.sources,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        cache_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _fetch_with_openai_web_search(
        target_name: str,
        api_key: str,
        model: str,
    ) -> DynamicKnowledge:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is not installed.") from exc

        prompt = f"""モンスターハンターワイルズの「{target_name}」について、狩猟中の音声アシスタントが使う攻略メモを作成してください。
Web検索を使い、可能なら攻略サイトや公式に近い情報を確認してください。

出力は日本語で、次の形式だけにしてください。
特徴: 1文
弱点属性: 1文
立ち回り: 2文以内
注意点: 2文以内

プレイヤーに読み上げる材料なので、長い説明、箇条書き記号、URL本文の引用は避けてください。
不確実な情報は「候補」「可能性」として表現してください。"""

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            tools=[{"type": "web_search"}],
            include=["web_search_call.action.sources"],
            input=prompt,
        )
        summary = response.output_text.strip()
        sources = _extract_source_urls(response)
        if not summary:
            raise RuntimeError("OpenAI returned an empty knowledge summary.")
        return DynamicKnowledge(
            target_name=target_name,
            summary=summary,
            sources=sources,
            cached=False,
        )


def _extract_source_urls(response: object) -> list[str]:
    urls: list[str] = []

    for item in getattr(response, "output", []) or []:
        action = getattr(item, "action", None)
        for source in getattr(action, "sources", []) or []:
            url = getattr(source, "url", None)
            if url:
                urls.append(str(url))
        for source in getattr(item, "sources", []) or []:
            url = getattr(source, "url", None)
            if url:
                urls.append(str(url))
        for content in getattr(item, "content", []) or []:
            for annotation in getattr(content, "annotations", []) or []:
                url = getattr(annotation, "url", None)
                if url:
                    urls.append(str(url))

    unique_urls: list[str] = []
    for url in urls:
        if url not in unique_urls:
            unique_urls.append(url)
    return unique_urls[:8]
