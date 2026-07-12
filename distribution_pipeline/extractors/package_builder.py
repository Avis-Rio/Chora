from __future__ import annotations

import json
import re
from pathlib import Path

from distribution_pipeline.assets.image_assets import build_image_asset_plan
from distribution_pipeline.directors.card_copy import build_card_copies
from distribution_pipeline.directors.visual_brief import build_visual_briefs
from distribution_pipeline.directors.visual_system import build_visual_system
from distribution_pipeline.extractors.insight_parser import (
    parse_insights,
    parse_philosophical_epilogue,
    parse_tags,
)
from distribution_pipeline.extractors.metadata_parser import parse_metadata


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _detect_platform(folder_name: str) -> str:
    if "youtube_" in folder_name:
        return "youtube"
    if "xiaoyuzhou_" in folder_name:
        return "xiaoyuzhou"
    return "unknown"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fa5-]+", "-", text).strip("-")
    return slug[:80] or "distribution-package"


def build_content_package(content_dir: Path, output_dir: Path | None = None) -> dict:
    content_dir = Path(content_dir)
    if output_dir is None:
        output_dir = Path("distribution") / _slugify(content_dir.name)
    else:
        output_dir = Path(output_dir)

    metadata_path = content_dir / "metadata.md"
    rewritten_path = content_dir / "rewritten.md"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata.md: {metadata_path}")
    if not rewritten_path.exists():
        raise FileNotFoundError(f"Missing rewritten.md: {rewritten_path}")

    source = parse_metadata(metadata_path)
    source.update(
        {
            "platform": _detect_platform(content_dir.name),
            "content_dir": str(content_dir),
            "tags": parse_tags(rewritten_path),
        }
    )
    insights = parse_insights(rewritten_path)
    philosophical_epilogue = parse_philosophical_epilogue(rewritten_path)
    visual_system = build_visual_system(source, insights)
    visual_briefs = build_visual_briefs(insights, visual_system)
    card_copy = build_card_copies(source, insights, philosophical_epilogue, visual_briefs)
    image_assets = build_image_asset_plan(source, insights, visual_briefs, visual_system, content_dir)

    _write_json(output_dir / "source.json", source)
    _write_json(output_dir / "insights.json", insights)
    _write_json(output_dir / "philosophical_epilogue.json", philosophical_epilogue)
    _write_json(output_dir / "visual_system.json", visual_system)
    _write_json(output_dir / "visual_briefs.json", visual_briefs)
    _write_json(output_dir / "card_copy.json", card_copy)
    _write_json(output_dir / "image_assets.json", image_assets)

    return {
        "source": source,
        "insights": insights,
        "philosophical_epilogue": philosophical_epilogue,
        "visual_system": visual_system,
        "visual_briefs": visual_briefs,
        "card_copy": card_copy,
        "image_assets": image_assets,
        "output_dir": str(output_dir),
    }
