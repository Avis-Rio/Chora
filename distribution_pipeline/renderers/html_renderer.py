from html import escape

from distribution_pipeline.renderers.templates import BASE_CARD_TEMPLATE


def _style_value(style: dict, path: list[str], default):
    value = style
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def render_card_html(card: dict, visual_brief: dict, style: dict, spec: dict) -> str:
    base_colors = _style_value(style, ["color", "base"], ["#F4EFE6", "#191713"])
    accents = _style_value(style, ["color", "accents"], ["#D75A2A"])
    typography = style.get("typography", {})
    width = int(spec["width"])
    height = int(spec["height"])
    scale = min(width / 1080, height / 1440)

    return BASE_CARD_TEMPLATE.format(
        width=width,
        height=height,
        padding=max(42, int(76 * scale)),
        brand_offset=max(30, int(56 * scale)),
        bg=escape(str(base_colors[0])),
        fg=escape(str(base_colors[1] if len(base_colors) > 1 else "#191713")),
        accent=escape(str(accents[0])),
        title_font=escape(str(typography.get("title_font", "serif"))),
        body_font=escape(str(typography.get("body_font", "sans-serif"))),
        title_size=max(42, int(72 * scale)),
        body_size=max(24, int(34 * scale)),
        style_id=escape(str(style.get("id", "unknown"))),
        card_type=escape(str(card.get("type", "single-insight"))),
        index=escape(str(card.get("index", ""))).zfill(2) if card.get("index") else "",
        title=escape(str(card.get("title", ""))),
        body=escape(str(card.get("body", ""))),
        metaphor=escape(str(visual_brief.get("visual_metaphor", ""))),
    )
