from __future__ import annotations

from .monster_knowledge import get_monster_knowledge


def format_prediction_lines(top_candidates: list[dict]) -> str:
    if not top_candidates:
        return "- unknown: 0.0%"
    return "\n".join(
        f"- {item['label']}: {float(item['confidence']):.1%}"
        for item in top_candidates
    )


def build_knowledge_block(monster_name: str) -> str:
    knowledge = get_monster_knowledge(monster_name)
    if not knowledge:
        return "登録済み基礎情報: なし。画像と推論結果を見て、不確実性を明示してください。"
    return (
        "登録済み基礎情報:\n"
        f"- 特徴: {knowledge.features}\n"
        f"- 弱点属性: {knowledge.weakness}\n"
        f"- 補足: {knowledge.notes or 'なし'}"
    )


def build_hunt_advice_prompt(event: dict) -> str:
    prediction_lines = format_prediction_lines(event["top_candidates"])
    monster_name = event["predicted_monster"]
    knowledge_block = build_knowledge_block(monster_name)

    if event["is_first_advice"]:
        return f"""あなたはモンスターハンターワイルズの狩猟支援AIです。
プレイヤーが狩猟を開始した直後です。画面認識では主なモンスターを「{monster_name}」と推定しました。

推論候補:
{prediction_lines}

{knowledge_block}

初回の情報提供として、次の2点だけを日本語で短く伝えてください。
1. モンスターの特徴
2. 弱点属性

推定に自信が低い場合は「推定では」と前置きしてください。
ゲーム中に聞き取りやすいように、説明調ではなく、落ち着いた短い声かけにしてください。"""

    return f"""あなたはモンスターハンターワイルズの狩猟支援AIです。
プレイヤーは狩猟中です。返答は1文、長くても2文までにしてください。

狩猟セッション:
- hunt_id: {event["hunt_id"]}
- turn_count: {event["turn_count"]}
- elapsed_seconds: {event["elapsed_seconds"]}

画像分類の推定:
- predicted_monster: {monster_name}
- confidence: {float(event["confidence"]):.1%}

推論候補:
{prediction_lines}

{knowledge_block}

画像も確認したうえで、今すぐ役立つ助言を1つだけ話してください。
候補: 回避、回復、距離取り、狙う部位、属性武器、罠、状態異常、立ち回り。
不確実なら安全側の助言を優先してください。
ナースロボ＿タイプＴの落ち着いた短い声かけとして自然にしてください。"""
