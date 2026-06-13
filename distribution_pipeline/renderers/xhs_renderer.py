from pathlib import Path

from distribution_pipeline.directors.style_loader import load_style
from distribution_pipeline.renderers.html_renderer import render_card_html
from distribution_pipeline.renderers.platform_specs import get_platform_spec
from distribution_pipeline.renderers.xhs_copy import build_xhs_publish_md
from distribution_pipeline.renderers.xhs_plan import build_xhs_card_plan


def _brief_for_card(card: dict, briefs: list[dict]) -> dict:
    insight_index = card.get("insight_index")
    for brief in briefs:
        if brief.get("insight_index") == insight_index:
            return brief
    return briefs[0] if briefs else {"visual_metaphor": "", "composition": {}}


def _card_filename(card: dict, index: int) -> str:
    suffix = {
        "cover-poster": "cover",
        "single-insight": "insight",
        "concept-map": "concept",
        "closing-card": "closing",
    }.get(card.get("type"), "card")
    return f"{index:02d}-{suffix}.html"


def _build_post_md(source: dict, insights: list[dict]) -> str:
    return build_xhs_publish_md(source, insights)


def render_xhs_package(package: dict, package_dir: Path, style_id: str = "chora-editorial", max_cards: int = 8) -> list[Path]:
    package_dir = Path(package_dir)
    cards_dir = package_dir / "xhs" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    style = load_style(style_id)
    spec = get_platform_spec("xhs")
    source = package["source"]
    insights = package["insights"]
    briefs = package.get("visual_briefs", [])
    plan = build_xhs_card_plan(source, insights, max_cards=max_cards)
    written = []

    for index, card in enumerate(plan, start=1):
        html = render_card_html(card, _brief_for_card(card, briefs), style, spec)
        path = cards_dir / _card_filename(card, index)
        path.write_text(html, encoding="utf-8")
        written.append(path)

    (package_dir / "xhs" / "post.md").write_text(_build_post_md(source, insights), encoding="utf-8")
    return written
