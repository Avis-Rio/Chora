import pytest

from distribution_pipeline.renderers.guizang.theme import resolve_theme


def test_resolve_editorial_theme():
    theme = resolve_theme("editorial", "indigo-porcelain")

    assert theme == {"attribute": "data-theme", "value": "indigo-porcelain"}


def test_resolve_swiss_theme():
    theme = resolve_theme("swiss", "ikb")

    assert theme == {"attribute": "data-accent", "value": "ikb"}


def test_reject_theme_from_wrong_mode():
    with pytest.raises(ValueError, match="not valid for guizang mode"):
        resolve_theme("editorial", "ikb")
