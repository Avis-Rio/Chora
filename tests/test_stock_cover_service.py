import pytest

from stock_cover_service import (
    _build_search_query,
    _download_image,
    _is_placeholder,
    _resize_to_16x9,
)


def test_is_placeholder():
    assert _is_placeholder("")
    assert _is_placeholder("your_api_key_here")
    assert _is_placeholder("***")
    assert not _is_placeholder("abc123")


def test_build_search_query_removes_episode_numbers():
    q = _build_search_query("午后偏见044｜书之爱：王强谈西文书籍的阅读、收藏与翻译")
    assert "044" not in q
    assert "午后偏见" not in q
    assert "书之爱" in q or "王强" in q or "西文书籍" in q


def test_build_search_query_english():
    q = _build_search_query("AI Revolution: The Future of Work")
    assert "AI" in q
    assert "Revolution" in q
    assert "Future" in q


def test_build_search_query_limit_terms():
    q = _build_search_query("a b c d e f g h i", max_terms=6)
    assert len(q.split()) <= 6


def test_download_image(tmp_path):
    # This test requires network; skip if SSL issues in CI.
    url = "https://picsum.photos/300/200"
    output = tmp_path / "down.jpg"
    if not _download_image(url, output):
        pytest.skip("Network download failed; skipping live download test")
    assert output.exists()


def test_resize_to_16x9(tmp_path):
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not available")

    img = Image.new("RGB", (1200, 900), color=(255, 0, 0))
    path = tmp_path / "wide.jpg"
    img.save(path, "JPEG")

    assert _resize_to_16x9(path)

    with Image.open(path) as resized:
        ratio = resized.width / resized.height
        assert 1.77 <= ratio <= 1.78
