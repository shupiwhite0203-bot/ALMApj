from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonsterKnowledge:
    name: str
    features: str
    weakness: str
    notes: str = ""


MONSTER_KNOWLEDGE: dict[str, MonsterKnowledge] = {
    "レ・ダウ": MonsterKnowledge(
        name="レ・ダウ",
        features="雷をまとった飛竜。帯電行動と遠距離からの雷撃に注意し、攻撃後の硬直を狙う。",
        weakness="氷属性が有力。ゲーム内ハンターノートの最新表示を優先する。",
        notes="雷耐性や気絶対策を優先すると安定しやすい。",
    ),
    "リオレウス": MonsterKnowledge(
        name="リオレウス",
        features="空中戦が多い火竜。火属性ブレス、毒爪、飛行中の突進に注意する。",
        weakness="雷属性、龍属性が候補。ゲーム内ハンターノートの最新表示を優先する。",
        notes="閃光、毒対策、火耐性が有効。",
    ),
    "リオレイア": MonsterKnowledge(
        name="リオレイア",
        features="地上戦主体の雌火竜。サマーソルトの毒、突進、火球に注意する。",
        weakness="雷属性、龍属性が候補。ゲーム内ハンターノートの最新表示を優先する。",
        notes="尻尾攻撃後や火球後の隙を狙う。",
    ),
    "アルシュベルド": MonsterKnowledge(
        name="アルシュベルド",
        features="鎖刃状の翼腕を使う白い孤影。距離を詰める連撃と広い攻撃範囲に注意する。",
        weakness="龍属性が候補。ゲーム内ハンターノートの最新表示を優先する。",
        notes="正面に居続けず、攻撃後に側面へ回る。",
    ),
    "チャタカブラ": MonsterKnowledge(
        name="チャタカブラ",
        features="舌と粘着物を使う両生種。正面の舌攻撃、突進、拘束気味の動きに注意する。",
        weakness="雷属性が候補。ゲーム内ハンターノートの最新表示を優先する。",
        notes="距離を取りすぎると舌攻撃を受けやすい。側面から攻める。",
    ),
}


def get_monster_knowledge(name: str) -> MonsterKnowledge | None:
    return MONSTER_KNOWLEDGE.get(name)
