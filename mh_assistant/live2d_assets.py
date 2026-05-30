from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Live2DAssetBundle:
    source_dir: Path
    output_dir: Path
    model_json: Path
    model_url_path: str


DEFAULT_NURSE_ROBOT_LIVE2D_DIR = (
    Path.home()
    / "Desktop"
    / "\u5b9f\u6cc1"
    / "\u305d\u3056\u3044"
    / "\u7acb\u3061\u7d75\u3044\u308d\u3044\u308d"
    / "\u30ca\u30fc\u30b9\u30ed\u30dc_\u30bf\u30a4\u30d7T"
    / "\u30ca\u30fc\u30b9\u30ed\u30dc\uff3f\u30bf\u30a4\u30d7\uff34\u516c\u5f0f\u7acb\u3061\u7d75\u7d20\u67502.0"
    / "\u30ca\u30fc\u30b9\u30ed\u30dc_Live2D_V50"
)


def prepare_nurse_robot_assets(
    source_dir: Path = DEFAULT_NURSE_ROBOT_LIVE2D_DIR,
    output_dir: Path = Path("runs/live2d_model/nurse_robot_type_t"),
) -> Live2DAssetBundle:
    """Copy the Nurse Robot Type T Live2D files into ALMApj with URL-safe names."""

    source_model = next(source_dir.glob("*.model3.json"))
    model_data = json.loads(source_model.read_text(encoding="utf-8"))
    refs = model_data["FileReferences"]

    output_dir.mkdir(parents=True, exist_ok=True)
    texture_dir = output_dir / "textures"
    texture_dir.mkdir(parents=True, exist_ok=True)

    moc_source = _existing_ref(source_dir, refs.get("Moc"), "*.moc3")
    display_source = _existing_ref(source_dir, refs.get("DisplayInfo"), "*.cdi3.json")
    physics_source = _optional_existing_ref(source_dir, refs.get("Physics"), "*.physics3.json")

    shutil.copy2(moc_source, output_dir / "nurse_robot_type_t.moc3")
    shutil.copy2(display_source, output_dir / "nurse_robot_type_t.cdi3.json")
    if physics_source:
        shutil.copy2(physics_source, output_dir / "nurse_robot_type_t.physics3.json")

    texture_paths: list[str] = []
    for index, texture_ref in enumerate(refs.get("Textures", [])):
        texture_source = _existing_ref(source_dir, texture_ref, "**/texture_*.png")
        texture_name = f"texture_{index:02d}{texture_source.suffix.lower()}"
        shutil.copy2(texture_source, texture_dir / texture_name)
        texture_paths.append(f"textures/{texture_name}")

    refs["Moc"] = "nurse_robot_type_t.moc3"
    refs["DisplayInfo"] = "nurse_robot_type_t.cdi3.json"
    if physics_source:
        refs["Physics"] = "nurse_robot_type_t.physics3.json"
    else:
        refs.pop("Physics", None)
    refs["Textures"] = texture_paths

    output_model = output_dir / "nurse_robot_type_t.model3.json"
    output_model.write_text(
        json.dumps(model_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return Live2DAssetBundle(
        source_dir=source_dir,
        output_dir=output_dir,
        model_json=output_model,
        model_url_path="/live2d-model/nurse_robot_type_t/nurse_robot_type_t.model3.json",
    )


def _existing_ref(source_dir: Path, ref: str | None, fallback_pattern: str) -> Path:
    result = _optional_existing_ref(source_dir, ref, fallback_pattern)
    if result:
        return result
    raise FileNotFoundError(f"Live2D asset not found: {ref or fallback_pattern}")


def _optional_existing_ref(source_dir: Path, ref: str | None, fallback_pattern: str) -> Path | None:
    if ref:
        candidate = source_dir / ref
        if candidate.exists():
            return candidate

    matches = sorted(source_dir.glob(fallback_pattern))
    return matches[0] if matches else None
