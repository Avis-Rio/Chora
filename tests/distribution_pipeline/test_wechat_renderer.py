from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.wechat_renderer import render_wechat_package


def test_render_wechat_package_writes_hero_inline_and_appendix(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package_dir = tmp_path / "distribution" / "token-economics"
    package = build_content_package(content_dir, package_dir)

    render_wechat_package(package, package_dir, style_id="chora-editorial")

    assert (package_dir / "wechat" / "hero.html").exists()
    assert len(list((package_dir / "wechat").glob("inline_*.html"))) >= 1
    assert (package_dir / "wechat" / "appendix.md").exists()
