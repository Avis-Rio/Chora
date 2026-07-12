import pytest

from distribution_pipeline.renderers.html_to_image import _generate_thumbnails, discover_html_outputs


def test_discover_html_outputs_finds_cards(tmp_path):
    cards = tmp_path / "xhs" / "cards"
    cards.mkdir(parents=True)
    (cards / "01-cover.html").write_text("<html></html>", encoding="utf-8")

    outputs = discover_html_outputs(tmp_path)

    assert outputs == [cards / "01-cover.html"]


def test_generate_thumbnails_creates_360px_images(tmp_path):
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not available")

    img = Image.new("RGB", (1080, 1440), color=(255, 0, 0))
    img.save(tmp_path / "card.png", "PNG")

    thumbs = _generate_thumbnails(tmp_path, width=360)

    assert len(thumbs) == 1
    assert thumbs[0].name == "card_thumb360.png"
    with Image.open(thumbs[0]) as thumb:
        assert thumb.size[0] == 360
        assert thumb.size[1] == 480
