SPECS = {
    "xhs": {"width": 1080, "height": 1440, "max_cards": 8},
    "xhs_square": {"width": 1080, "height": 1080, "max_cards": 8},
    "wechat_hero": {"width": 1200, "height": 675, "max_cards": 1},
    "wechat_inline": {"width": 900, "height": 500, "max_cards": 3},
}


def get_platform_spec(name: str) -> dict:
    if name not in SPECS:
        raise ValueError(f"Unknown platform spec: {name}")
    return dict(SPECS[name])
