from distribution_pipeline.directors.style_loader import load_style


def test_load_style_returns_required_sections():
    style = load_style("chora-editorial")

    assert style["id"] == "chora-editorial"
    assert "typography" in style
    assert "color" in style
    assert "layout" in style
    assert "avoid" in style
