from distribution_pipeline.renderers.html_to_image import discover_html_outputs


def test_discover_html_outputs_finds_cards(tmp_path):
    cards = tmp_path / "xhs" / "cards"
    cards.mkdir(parents=True)
    (cards / "01-cover.html").write_text("<html></html>", encoding="utf-8")

    outputs = discover_html_outputs(tmp_path)

    assert outputs == [cards / "01-cover.html"]
