from pathlib import Path

from distribution_pipeline.extractors.metadata_parser import parse_metadata


def test_parse_metadata_extracts_core_fields():
    path = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/metadata.md")

    data = parse_metadata(path)

    assert data["title"] == "Token经济学：AI时代的新货币战争"
    assert data["channel"] == "硅谷101"
    assert data["source_url"] == "https://www.youtube.com/watch?v=example12345"
    assert data["publish_date"] == "2026-05-13"
    assert "肖志斌" in data["guests"]
    assert len(data["quotes"]) == 2
