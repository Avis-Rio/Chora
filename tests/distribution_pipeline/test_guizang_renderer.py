from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_xhs_package


def test_render_guizang_xhs_package_writes_single_index(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    written = render_guizang_xhs_package(
        package,
        tmp_path / "pkg",
        max_cards=6,
        mode="editorial",
        theme="indigo-porcelain",
    )

    html_path = tmp_path / "pkg" / "xhs" / "index.html"
    assert html_path in written
    html = html_path.read_text(encoding="utf-8")
    assert 'data-theme="indigo-porcelain"' in html
    assert html.count('class="poster xhs"') >= 2
    assert "Theme tokens" in html
    assert "Magazine WebGL background" in html
    assert "[标题占位]" not in html
    assert (tmp_path / "pkg" / "xhs" / "post.md").exists()
    assert (tmp_path / "pkg" / "xhs" / "render.cjs").exists()
    assert (tmp_path / "pkg" / "xhs" / "assets" / "magazine-bg-webgl.js").exists()
    assert (tmp_path / "pkg" / "xhs" / "assets" / "SOURCES.md").exists()
    assert (tmp_path / "pkg" / "xhs" / "assets" / "image_assets.json").exists()
    assert (tmp_path / "pkg" / "xhs" / "assets" / "brand" / "rhizomata-qr.png").exists()
    assert not (tmp_path / "pkg" / "xhs" / "assets" / "images" / "source-cover.jpg").exists()
    assert 'src="assets/images/source-cover.jpg"' not in html
    assert 'src="assets/images/xhs-02-evidence.svg"' in html
    assert 'src="assets/brand/rhizomata-qr.png"' in html
    assert "阅读全文 · Chora" in html
    post = (tmp_path / "pkg" / "xhs" / "post.md").read_text(encoding="utf-8")
    assert "## 小红书正文｜复制此段" in post
    assert "## Tags｜复制此段" in post


def test_render_guizang_xhs_package_auto_theme_routes_creator_growth(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")
    package["source"]["title"] = "How To Grow An Audience If You Have 0 Followers"
    package["source"]["channel"] = "Dan Koe"
    package["insights"] = [
        {
            "index": 1,
            "title": "互惠原则是社交增长的底层机制",
            "body": "真实关系是增长的手动杠杆。",
        }
    ]

    render_guizang_xhs_package(
        package,
        tmp_path / "pkg",
        max_cards=4,
        mode="editorial",
        theme="auto",
    )

    html = (tmp_path / "pkg" / "xhs" / "index.html").read_text(encoding="utf-8")

    assert 'data-theme="kraft-paper"' in html
    assert "从零粉丝开始" in html


def test_render_guizang_xhs_package_auto_theme_routes_solitude_psychology(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")
    package["source"]["title"] = "Why People Disappear | The Psychology of Being Alone"
    package["source"]["channel"] = "Aperture"
    package["insights"] = [
        {
            "index": 1,
            "title": "孤独与孤寂的根本区别",
            "body": "孤独是主动选择，孤寂是渴望连接的痛苦。",
        }
    ]

    render_guizang_xhs_package(
        package,
        tmp_path / "pkg",
        max_cards=4,
        mode="editorial",
        theme="auto",
    )

    html = (tmp_path / "pkg" / "xhs" / "index.html").read_text(encoding="utf-8")

    assert 'data-theme="midnight-ink"' in html
    assert "为什么越来越多人" in html
