import re
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_wechat_package


def test_render_guizang_wechat_package_writes_cover_pair(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    written = render_guizang_wechat_package(
        package,
        tmp_path / "pkg",
        mode="editorial",
        theme="auto",
    )

    wechat_dir = tmp_path / "pkg" / "wechat"
    html_path = wechat_dir / "index.html"
    render_path = wechat_dir / "render.cjs"
    appendix_path = wechat_dir / "appendix.md"
    html = html_path.read_text(encoding="utf-8")
    render_script = render_path.read_text(encoding="utf-8")
    appendix = appendix_path.read_text(encoding="utf-8")

    assert html_path in written
    assert appendix_path in written
    assert render_path in written
    assert 'id="wechat-21x9"' in html
    assert 'id="wechat-1x1"' in html
    assert 'id="wechat-cover-pair-preview"' in html
    assert 'class="poster wide"' in html
    assert 'class="poster square"' in html
    assert "AI 成本" in html
    wide_h1 = re.search(r'id="wechat-21x9".*?<h1[^>]*>(.*?)</h1>', html, re.S)
    assert wide_h1
    assert "<br>" not in wide_h1.group(1)
    assert "wechat-21x9-cover.png" in render_script
    assert "wechat-1x1-cover.png" in render_script
    assert "wechat-cover-pair-preview.png" in render_script
    assert "方形封面" in appendix
    assert (wechat_dir / "assets" / "image_assets.json").exists()
