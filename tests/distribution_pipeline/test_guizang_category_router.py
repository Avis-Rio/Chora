from distribution_pipeline.renderers.guizang.category_router import detect_rednote_category


def test_detect_rednote_category_uses_tags_title_and_insights():
    source = {"title": "三天两夜云南旅行路线", "channel": "Chora", "tags": ["旅行", "路线"]}
    insights = [{"title": "第一天先去古城", "body": "把行程压到可步行范围。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "travel"
    assert category["label"] == "旅行"
    assert "M02" in category["editorial"]
    assert category["scope"] == "in_scope"
    assert category["deck_sequence"]["editorial"][1] == "M02"


def test_detect_rednote_category_marks_workplace_as_swiss_first():
    source = {"title": "职场复盘系统", "channel": "Chora", "tags": ["效率"]}
    insights = [{"title": "流程决定复利", "body": "团队管理不是靠临场发挥。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "workplace"
    assert category["mode_hint"] == "swiss"
    assert "S06" in category["swiss"]
    assert category["deck_sequence"]["swiss"][1] == "S09"


def test_detect_rednote_category_surfaces_scope_notes_for_image_rights():
    source = {"title": "Elden Ring boss 战复盘", "channel": "Chora", "tags": ["游戏"]}
    insights = [{"title": "胜率不是唯一指标", "body": "通关体验来自路线和资源管理。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "game"
    assert category["scope"] == "needs_image_rights"
    assert category["scope_notes"]


def test_detect_rednote_category_ignores_single_generic_keyword():
    source = {"title": "谷歌 AI 的技术路线", "channel": "硅谷101"}
    insights = [{"title": "研究品位的本质是时间管理。", "body": "判断比执行更重要。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "default"
