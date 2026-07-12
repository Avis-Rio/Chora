from distribution_pipeline.renderers.guizang.guizang_renderer import build_wechat_render_targets
from distribution_pipeline.renderers.guizang.render_script import (
    build_render_script,
    build_xhs_render_targets,
)


def test_build_xhs_render_script_targets_posters():
    script = build_render_script(
        html_name="index.html",
        targets=[{"selector": "#xhs-01", "filename": "xhs-01-cover.png"}],
    )

    assert "#xhs-01" in script
    assert "xhs-01-cover.png" in script
    assert "chromium.launch" in script
    assert "_loadPlaywrightChromium" in script
    assert "process.env.GUIZANG_RENDERER" in script
    assert "Playwright launch failed, falling back to wkhtmltoimage" in script
    assert 'const { chromium } = require("playwright");' not in script
    assert r"/<style>[\s\S]*?<\/style>/" in script
    assert r"/<style>[\\s\\S]*?<\/style>/" not in script
    assert '"--width", String(size.width)' in script
    assert '"--height", String(size.height)' in script
    assert "path.join(root, `_tmp_${sectionId}.html`)" in script
    assert "path.join(outputDir, `_tmp_${sectionId}.html`)" not in script
    assert 'waitUntil: "domcontentloaded"' in script
    assert "networkidle" not in script
    # 系統 Chrome 兜底路徑是允許的（macOS 優先）
    assert "connectOverCDP" not in script


def test_build_xhs_render_targets_names_pages_by_role():
    pages = [
        {"id": "xhs-01", "role": "cover"},
        {"id": "xhs-02", "role": "insight"},
        {"id": "xhs-03", "role": "closing"},
    ]

    targets = build_xhs_render_targets(pages)

    assert targets == [
        {"selector": "#xhs-01", "filename": "xhs-01-cover.png", "width": 1080, "height": 1440},
        {"selector": "#xhs-02", "filename": "xhs-02-insight.png", "width": 1080, "height": 1440},
        {"selector": "#xhs-03", "filename": "xhs-03-closing.png", "width": 1080, "height": 1440},
    ]


def test_build_wechat_render_targets_include_platform_sizes():
    targets = build_wechat_render_targets()

    assert targets == [
        {"selector": "#wechat-21x9", "filename": "wechat-21x9-cover.png", "width": 2100, "height": 900},
        {"selector": "#wechat-1x1", "filename": "wechat-1x1-cover.png", "width": 1080, "height": 1080},
        {
            "selector": "#wechat-cover-pair-preview",
            "filename": "wechat-cover-pair-preview.png",
            "width": 2400,
            "height": 844,
        },
    ]
