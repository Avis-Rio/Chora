import pytest

from xiaoyuzhou_service import (
    EpisodeMetadata,
    _extract_from_html,
    _extract_from_json_ld,
    _extract_from_next_data,
    _extract_from_open_graph,
    _normalize_date,
    extract_episode_id,
    extract_guests_from_description,
    get_episode_metadata,
)


def test_extract_episode_id_from_url():
    url = "https://www.xiaoyuzhoufm.com/episode/5e4ff46a418a84a046973eee"
    assert extract_episode_id(url) == "5e4ff46a418a84a046973eee"


def test_extract_episode_id_from_raw_id():
    assert extract_episode_id("5e4ff46a418a84a046973eee") == "5e4ff46a418a84a046973eee"


def test_extract_episode_id_invalid():
    assert extract_episode_id("https://example.com/foo") is None
    assert extract_episode_id("") is None


def test_extract_from_next_data_complete():
    next_data = {
        "props": {
            "pageProps": {
                "episode": {
                    "title": "Test Episode",
                    "pubDate": "2024-03-15T08:00:00.000Z",
                    "description": "嘉宾：Alice，Bob",
                    "podcast": {"title": "Test Podcast"},
                    "trial": {"segment": "https://audio.example.com/trial.m4a"},
                }
            }
        }
    }
    result = _extract_from_next_data(next_data)
    assert result["title"] == "Test Episode"
    assert result["channel"] == "Test Podcast"
    assert result["upload_date"] == "2024-03-15"
    assert result["audio_url"] == "https://audio.example.com/trial.m4a"
    assert "Alice" in result["description"]


def test_extract_from_next_data_fallback_audio():
    next_data = {
        "props": {
            "pageProps": {
                "episode": {
                    "title": "No Trial",
                    "pubDate": "",
                    "podcast": {"title": "Pod"},
                    "enclosure": {"url": "https://audio.example.com/full.m4a"},
                }
            }
        }
    }
    result = _extract_from_next_data(next_data)
    assert result["audio_url"] == "https://audio.example.com/full.m4a"


def test_extract_from_json_ld_podcast_episode():
    json_ld = [
        {
            "@type": "PodcastEpisode",
            "name": "LD Episode",
            "datePublished": "2024-01-20",
            "description": "Desc",
            "audio": {"contentUrl": "https://audio.example.com/ld.m4a"},
            "partOfSeries": {"name": "LD Podcast"},
        }
    ]
    result = _extract_from_json_ld(json_ld)
    assert result["title"] == "LD Episode"
    assert result["channel"] == "LD Podcast"
    assert result["audio_url"] == "https://audio.example.com/ld.m4a"


def test_extract_from_open_graph():
    meta = {
        "og:title": "OG Title",
        "og:description": "OG Desc",
        "og:audio": "https://audio.example.com/og.m4a",
    }
    result = _extract_from_open_graph(meta)
    assert result["title"] == "OG Title"
    assert result["audio_url"] == "https://audio.example.com/og.m4a"


def test_extract_from_open_graph_empty():
    assert _extract_from_open_graph({}) is None


def test_extract_from_html():
    html = """
    <html>
      <head><title>HTML Title | 小宇宙</title></head>
      <body>
        <audio src="https://audio.example.com/audio.m4a" controls></audio>
        <meta name="description" content="HTML Desc">
      </body>
    </html>
    """
    result = _extract_from_html(html)
    assert result["title"] == "HTML Title | 小宇宙"
    assert result["audio_url"] == "https://audio.example.com/audio.m4a"


def test_extract_from_html_no_data():
    assert _extract_from_html("<html></html>") is None


def test_normalize_date_iso():
    assert _normalize_date("2024-05-20T10:00:00Z") == "2024-05-20"
    assert _normalize_date("2024-05-20") == "2024-05-20"


def test_normalize_date_empty():
    result = _normalize_date("")
    assert len(result) == 10 and result.count("-") == 2


def test_extract_guests_from_description():
    desc = "本期嘉宾：张三、李四。\n\n其他内容"
    assert "张三" in extract_guests_from_description(desc)
    assert "李四" in extract_guests_from_description(desc)


def test_extract_guests_from_description_colon():
    desc = "嘉宾: Alice, Bob"
    assert extract_guests_from_description(desc) == "Alice, Bob"


def test_extract_guests_empty():
    assert extract_guests_from_description("") == ""


def test_episode_metadata_to_dict():
    meta = EpisodeMetadata(
        title="T",
        channel="C",
        upload_date="2024-01-01",
        audio_url="https://a.com/x.m4a",
        episode_id="abc123",
        description="D",
        guests="G",
        source_url="https://x.com/e/abc123",
        raw={},
    )
    d = meta.to_dict()
    assert d["title"] == "T"
    assert d["audio_url"] == "https://a.com/x.m4a"


@pytest.mark.skip(reason="Requires network access to xiaoyuzhoufm.com")
def test_get_episode_metadata_integration():
    # Use a known public episode URL or ID for manual/CI integration tests.
    meta = get_episode_metadata("https://www.xiaoyuzhoufm.com/episode/5e4ff46a418a84a046973eee")
    assert meta.title
    assert meta.audio_url
    assert meta.episode_id
