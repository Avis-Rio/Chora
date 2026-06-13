EDITORIAL_THEMES = {
    "ink-classic",
    "indigo-porcelain",
    "forest-ink",
    "kraft-paper",
    "dune",
    "midnight-ink",
}

SWISS_THEMES = {
    "ikb",
    "lemon-yellow",
    "lemon-green",
    "safety-orange",
}


def resolve_theme(mode: str, theme: str) -> dict[str, str]:
    if mode == "editorial":
        if theme not in EDITORIAL_THEMES:
            raise ValueError(f"{theme} is not valid for guizang mode {mode}")
        return {"attribute": "data-theme", "value": theme}
    if mode == "swiss":
        if theme not in SWISS_THEMES:
            raise ValueError(f"{theme} is not valid for guizang mode {mode}")
        return {"attribute": "data-accent", "value": theme}
    raise ValueError(f"Unknown guizang mode: {mode}")
