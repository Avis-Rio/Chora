from distribution_pipeline.renderers.platform_specs import get_platform_spec


def test_xhs_spec_uses_vertical_card_size():
    spec = get_platform_spec("xhs")

    assert spec["width"] == 1080
    assert spec["height"] == 1440
    assert spec["max_cards"] == 8


def test_wechat_spec_uses_horizontal_hero_size():
    spec = get_platform_spec("wechat_hero")

    assert spec["width"] == 1200
    assert spec["height"] == 675
