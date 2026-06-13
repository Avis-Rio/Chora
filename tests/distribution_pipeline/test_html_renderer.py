from distribution_pipeline.renderers.html_renderer import render_card_html


def test_render_card_html_includes_text_and_dimensions():
    card = {
        "type": "single-insight",
        "title": "计量即权力",
        "body": "谁定义 Token 的计量方式，谁就定义 AI 经济的边界。",
        "index": 3,
    }
    visual_brief = {
        "visual_metaphor": "仪表盘连接着发光账本",
        "composition": {"text_position": "left-top"},
        "mood": "冷静、制度化",
    }
    style = {
        "id": "chora-editorial",
        "color": {"base": ["#F4EFE6", "#191713"], "accents": ["#D75A2A"]},
        "typography": {"title_font": "serif", "body_font": "sans-serif"},
    }
    spec = {"width": 1080, "height": 1440}

    html = render_card_html(card, visual_brief, style, spec)

    assert "计量即权力" in html
    assert "1080px" in html
    assert "1440px" in html
    assert "仪表盘连接着发光账本" in html
