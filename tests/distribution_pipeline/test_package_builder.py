import json
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package


def test_build_content_package_combines_metadata_and_insights(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    output_dir = tmp_path / "distribution" / "token-economics"

    package = build_content_package(content_dir, output_dir)

    assert (output_dir / "source.json").exists()
    assert (output_dir / "insights.json").exists()
    assert (output_dir / "visual_system.json").exists()
    assert (output_dir / "visual_briefs.json").exists()
    assert (output_dir / "image_assets.json").exists()
    assert package["source"]["title"] == "Token经济学：AI时代的新货币战争"
    assert package["source"]["platform"] == "youtube"
    assert package["source"]["tags"] == ["Technology", "Economics", "Power & Politics"]
    assert len(package["insights"]) == 8
    assert package["visual_system"]["visual_motifs"]
    assert len(package["visual_briefs"]) == 8
    assert package["image_assets"]["requests"]
    assert package["image_assets"]["local_assets"][0]["asset_id"] == "source-cover"

    source = json.loads((output_dir / "source.json").read_text(encoding="utf-8"))
    assert source["channel"] == "硅谷101"
