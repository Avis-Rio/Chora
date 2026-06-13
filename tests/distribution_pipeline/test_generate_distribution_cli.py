from pathlib import Path

from distribution_pipeline.generate_distribution import run


def test_run_generates_all_platform_outputs(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    output_root = tmp_path / "distribution"

    package_dir = run(
        content_dir=content_dir,
        output_root=output_root,
        platform="all",
        style_id="chora-editorial",
        max_cards=5,
        export_images=False,
    )

    assert (package_dir / "source.json").exists()
    assert (package_dir / "xhs" / "post.md").exists()
    assert (package_dir / "wechat" / "appendix.md").exists()
    assert (package_dir / "manifest.json").exists()


def test_basic_renderer_still_generates_current_shape(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")

    package_dir = run(
        content_dir=content_dir,
        output_root=tmp_path,
        platform="xhs",
        renderer="basic",
        export_images=False,
    )

    assert (package_dir / "xhs" / "cards" / "01-cover.html").exists()
    assert (package_dir / "xhs" / "post.md").exists()


def test_guizang_renderer_generates_xhs_index(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")

    package_dir = run(
        content_dir=content_dir,
        output_root=tmp_path,
        platform="xhs",
        renderer="guizang",
        export_images=False,
    )

    assert (package_dir / "xhs" / "index.html").exists()
    assert (package_dir / "xhs" / "post.md").exists()
    assert (package_dir / "xhs" / "render.cjs").exists()


def test_guizang_no_export_skips_browser_validator(tmp_path, monkeypatch):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")

    def fail_validator(*_args, **_kwargs):
        raise AssertionError("validator should not run when export_images is false")

    monkeypatch.setattr("distribution_pipeline.generate_distribution.run_guizang_validator", fail_validator)

    package_dir = run(
        content_dir=content_dir,
        output_root=tmp_path,
        platform="xhs",
        renderer="guizang",
        export_images=False,
    )

    manifest = (package_dir / "manifest.json").read_text(encoding="utf-8")
    assert "image export is disabled" in manifest


def test_guizang_renderer_receives_image_asset_mode(tmp_path, monkeypatch):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    captured = {}

    def fake_render(package, package_dir, max_cards, mode, theme, image_asset_mode):
        captured["image_asset_mode"] = image_asset_mode
        xhs_dir = package_dir / "xhs"
        xhs_dir.mkdir(parents=True, exist_ok=True)
        for name in ("index.html", "post.md", "render.cjs"):
            (xhs_dir / name).write_text(name, encoding="utf-8")
        return [xhs_dir / "index.html"]

    monkeypatch.setattr("distribution_pipeline.generate_distribution.render_guizang_xhs_package", fake_render)
    monkeypatch.setattr(
        "distribution_pipeline.generate_distribution.run_guizang_validator",
        lambda *_args, **_kwargs: {"status": "skipped"},
    )

    run(
        content_dir=content_dir,
        output_root=tmp_path,
        platform="xhs",
        renderer="guizang",
        export_images=False,
        image_asset_mode="download",
    )

    assert captured["image_asset_mode"] == "download"


def test_guizang_renderer_exports_images_when_enabled(tmp_path, monkeypatch):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    exported = []

    def fake_export(package_dir):
        exported.append(package_dir)
        return []

    monkeypatch.setattr("distribution_pipeline.generate_distribution.export_guizang_images", fake_export)
    monkeypatch.setattr(
        "distribution_pipeline.generate_distribution.run_guizang_validator",
        lambda *_args, **_kwargs: {"status": "skipped"},
    )

    package_dir = run(
        content_dir=content_dir,
        output_root=tmp_path,
        platform="xhs",
        renderer="guizang",
        export_images=True,
    )

    assert exported == [package_dir]


def test_guizang_wechat_renderer_generates_cover_pair(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")

    package_dir = run(
        content_dir=content_dir,
        output_root=tmp_path,
        platform="wechat",
        renderer="guizang",
        export_images=False,
    )

    assert (package_dir / "wechat" / "index.html").exists()
    assert (package_dir / "wechat" / "appendix.md").exists()
    assert (package_dir / "wechat" / "render.cjs").exists()
    manifest = (package_dir / "manifest.json").read_text(encoding="utf-8")
    assert '"wechat"' in manifest
    assert "image export is disabled" in manifest


def test_guizang_all_renderer_generates_xhs_and_wechat(tmp_path):
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")

    package_dir = run(
        content_dir=content_dir,
        output_root=tmp_path,
        platform="all",
        renderer="guizang",
        export_images=False,
    )

    assert (package_dir / "xhs" / "index.html").exists()
    assert (package_dir / "wechat" / "index.html").exists()
