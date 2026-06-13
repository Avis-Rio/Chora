from distribution_pipeline.renderers.guizang.render_script import build_render_script, build_xhs_render_targets


def test_build_xhs_render_script_targets_posters():
    script = build_render_script(
        html_name="index.html",
        targets=[{"selector": "#xhs-01", "filename": "xhs-01-cover.png"}],
    )

    assert "#xhs-01" in script
    assert "xhs-01-cover.png" in script
    assert "chromium.launch" in script
    assert 'waitUntil: "domcontentloaded"' in script
    assert "networkidle" not in script
    assert "/Applications/Google Chrome.app" not in script
    assert "connectOverCDP" not in script


def test_build_xhs_render_targets_names_pages_by_role():
    pages = [
        {"id": "xhs-01", "role": "cover"},
        {"id": "xhs-02", "role": "insight"},
        {"id": "xhs-03", "role": "closing"},
    ]

    targets = build_xhs_render_targets(pages)

    assert targets == [
        {"selector": "#xhs-01", "filename": "xhs-01-cover.png"},
        {"selector": "#xhs-02", "filename": "xhs-02-insight.png"},
        {"selector": "#xhs-03", "filename": "xhs-03-closing.png"},
    ]
