import pytest

from distribution_pipeline.renderers.guizang.template_loader import load_template


def test_load_editorial_template_contains_placeholder():
    html = load_template("editorial")

    assert "<!-- POSTERS_HERE -->" in html
    assert "data-theme" in html


def test_load_swiss_template_contains_placeholder():
    html = load_template("swiss")

    assert "<!-- POSTERS_HERE -->" in html
    assert "data-accent" in html


def test_load_template_rejects_unknown_mode():
    with pytest.raises(ValueError, match="Unknown guizang mode"):
        load_template("nope")
