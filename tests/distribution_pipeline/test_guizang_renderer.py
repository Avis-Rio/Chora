from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_wechat_package
from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_xhs_package
from distribution_pipeline.renderers.guizang.guizang_renderer import resolve_guizang_mode


def test_render_guizang_xhs_package_writes_single_index(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    written = render_guizang_xhs_package(
        package,
        tmp_path / "pkg",
        max_cards=6,
        mode="editorial",
        theme="indigo-porcelain",
        image_asset_mode="plan",
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
    # plan 模式按 workflow-rules.md 不生图，evidence.png 在 candidates/download 模式出现
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
        image_asset_mode="plan",
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
        image_asset_mode="plan",
    )

    html = (tmp_path / "pkg" / "xhs" / "index.html").read_text(encoding="utf-8")

    assert 'data-theme="midnight-ink"' in html
    assert "为什么越来越多人" in html


def test_resolve_guizang_mode_auto_routes_operational_ai_to_swiss():
    package = {
        "source": {"title": "硅谷101 Token经济学", "channel": "硅谷101", "tags": []},
        "insights": [
            {
                "index": 1,
                "title": "AI 成本正在重新分配权力",
                "body": "Token 单价、算力成本和价格分化决定下一轮模型竞争。",
            }
        ],
    }

    assert resolve_guizang_mode(package, "auto", target="xhs") == "swiss"


def test_resolve_guizang_mode_auto_routes_culture_and_psychology_to_editorial():
    museum = {
        "source": {"title": "当博物馆开始说话", "channel": "忽左忽右", "tags": []},
        "insights": [
            {
                "index": 1,
                "title": "客观性的幻觉",
                "body": "博物馆的展陈是文化权力、记忆与意识形态共同构建的叙事。",
            }
        ],
    }
    solitude = {
        "source": {"title": "Why People Disappear | The Psychology of Being Alone", "channel": "Aperture", "tags": []},
        "insights": [
            {
                "index": 1,
                "title": "孤独与孤寂的根本区别",
                "body": "孤独是主动选择，孤寂是渴望连接的痛苦。",
            }
        ],
    }

    assert resolve_guizang_mode(museum, "auto", target="xhs") == "editorial"
    assert resolve_guizang_mode(solitude, "auto", target="xhs") == "editorial"


def test_resolve_guizang_mode_wechat_supports_swiss():
    package = {
        "source": {"title": "Token 经济学", "channel": "硅谷101", "tags": ["Technology"]},
        "insights": [
            {
                "index": 1,
                "title": "成本结构的范式转移",
                "body": "传统 SaaS 的边际成本趋近于零，AI 时代的成本随用量线性增长。",
            }
        ],
    }

    assert resolve_guizang_mode(package, "auto", target="wechat") == "swiss"


def test_render_guizang_wechat_package_swiss_mode(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    written = render_guizang_wechat_package(
        package,
        tmp_path / "pkg",
        mode="swiss",
        theme="auto",
        image_asset_mode="plan",
    )

    html_path = tmp_path / "pkg" / "wechat" / "index.html"
    assert html_path in written
    html = html_path.read_text(encoding="utf-8")
    assert "wechat-21x9" in html
    assert "wechat-1x1" in html
    assert "SWISS" in html
    assert " wide swiss" in html
    assert " square swiss" in html



def test_render_guizang_xhs_package_swiss_map_recipe(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")
    package["source"]["title"] = "黄金东移与全球权力转移"
    package["insights"] = [
        {
            "index": 1,
            "title": "黄金正在从西方流向东方",
            "body": "中国、印度和中东央行持续增持黄金，而欧美投资者ETF持仓下降。",
        }
    ]

    render_guizang_xhs_package(
        package,
        tmp_path / "pkg",
        max_cards=4,
        mode="swiss",
        theme="auto",
        image_asset_mode="plan",
    )

    html = (tmp_path / "pkg" / "xhs" / "index.html").read_text(encoding="utf-8")

    assert "Map · Route" in html
    assert "西方" in html
    assert "东方" in html
    assert "card-fill" in html
