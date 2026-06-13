from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.xhs_renderer import render_xhs_package
from distribution_pipeline.renderers.xhs_renderer import _build_post_md


def test_render_xhs_package_writes_html_and_post(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package_dir = tmp_path / "distribution" / "token-economics"
    package = build_content_package(content_dir, package_dir)

    render_xhs_package(package, package_dir, style_id="chora-editorial", max_cards=5)

    assert (package_dir / "xhs" / "cards").exists()
    assert (package_dir / "xhs" / "post.md").exists()
    assert len(list((package_dir / "xhs" / "cards").glob("*.html"))) >= 3


def test_build_post_md_keeps_all_insights():
    source = {"title": "长文章", "channel": "Chora"}
    insights = [
        {"title": f"洞察{index}", "body": f"正文{index}"}
        for index in range(1, 8)
    ]

    post = _build_post_md(source, insights)

    assert "洞察1" in post
    assert "洞察7" in post
    assert "## 小红书正文｜复制此段" in post
    assert "## Tags｜复制此段" in post
    assert "#Chora" in post
