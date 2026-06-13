from pathlib import Path

from distribution_pipeline.directors.style_loader import load_style
from distribution_pipeline.renderers.html_renderer import render_card_html
from distribution_pipeline.renderers.platform_specs import get_platform_spec


def render_wechat_package(package: dict, package_dir: Path, style_id: str = "chora-editorial") -> list[Path]:
    package_dir = Path(package_dir)
    wechat_dir = package_dir / "wechat"
    wechat_dir.mkdir(parents=True, exist_ok=True)

    style = load_style(style_id)
    source = package["source"]
    insights = package["insights"]
    briefs = package.get("visual_briefs", [])
    written = []

    hero_card = {
        "type": "cover-poster",
        "title": source.get("title", "Chora"),
        "body": f"{source.get('channel', 'Unknown')} · Chora 深度内容",
        "index": 1,
    }
    hero_html = render_card_html(hero_card, briefs[0] if briefs else {}, style, get_platform_spec("wechat_hero"))
    hero_path = wechat_dir / "hero.html"
    hero_path.write_text(hero_html, encoding="utf-8")
    written.append(hero_path)

    for index, insight in enumerate(insights[:3], start=1):
        card = {
            "type": "single-insight",
            "title": insight.get("title", ""),
            "body": insight.get("body", ""),
            "index": index,
        }
        brief = briefs[index - 1] if index - 1 < len(briefs) else {}
        html = render_card_html(card, brief, style, get_platform_spec("wechat_inline"))
        path = wechat_dir / f"inline_{index:02d}.html"
        path.write_text(html, encoding="utf-8")
        written.append(path)

    appendix = (
        f"完整内容见 Chora：{source.get('title', '')}\n\n"
        "欢迎关注「Rhizomata」，接收片段、思考与延伸阅读。\n\n"
        f"原始来源：{source.get('source_url', '')}\n"
    )
    (wechat_dir / "appendix.md").write_text(appendix, encoding="utf-8")
    return written
