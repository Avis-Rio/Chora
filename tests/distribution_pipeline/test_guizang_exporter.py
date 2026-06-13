import subprocess
from pathlib import Path

import pytest

from distribution_pipeline.renderers.guizang.exporter import (
    PROJECT_PLAYWRIGHT_BROWSERS,
    discover_guizang_render_scripts,
    export_guizang_images,
)


def test_discover_guizang_render_scripts(tmp_path):
    (tmp_path / "xhs").mkdir()
    (tmp_path / "xhs" / "render.cjs").write_text("// test", encoding="utf-8")

    scripts = discover_guizang_render_scripts(tmp_path)

    assert scripts == [tmp_path / "xhs" / "render.cjs"]


def test_export_guizang_images_returns_output_pngs(tmp_path, monkeypatch):
    xhs_dir = tmp_path / "xhs"
    output_dir = xhs_dir / "output"
    output_dir.mkdir(parents=True)
    (xhs_dir / "render.cjs").write_text("// test", encoding="utf-8")
    image_path = output_dir / "xhs-01-cover.png"
    image_path.write_text("png", encoding="utf-8")

    calls = []

    def fake_run(args, cwd, check, text, env, timeout):
        calls.append((args, cwd, check, text, env, timeout))
        return subprocess.CompletedProcess(args, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    images = export_guizang_images(tmp_path)

    assert calls[0][0] == ["node", "render.cjs"]
    assert calls[0][1] == xhs_dir
    assert calls[0][4]["PLAYWRIGHT_BROWSERS_PATH"] == str(PROJECT_PLAYWRIGHT_BROWSERS)
    assert images == [image_path]


def test_export_guizang_images_reports_missing_node(tmp_path, monkeypatch):
    (tmp_path / "xhs").mkdir()
    (tmp_path / "xhs" / "render.cjs").write_text("// test", encoding="utf-8")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("node")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Guizang image export requires Node.js and Playwright"):
        export_guizang_images(tmp_path)


def test_export_guizang_images_reports_missing_playwright(tmp_path, monkeypatch):
    (tmp_path / "xhs").mkdir()
    (tmp_path / "xhs" / "render.cjs").write_text("// test", encoding="utf-8")

    def fake_run(args, cwd, check, text, env, timeout):
        raise subprocess.CalledProcessError(
            1,
            args,
            output="",
            stderr="Error: Cannot find module 'playwright'",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Guizang image export requires Node.js and Playwright"):
        export_guizang_images(tmp_path)
