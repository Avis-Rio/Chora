import subprocess
from pathlib import Path

from distribution_pipeline.renderers.guizang.validator import (
    PROJECT_PLAYWRIGHT_BROWSERS,
    parse_validator_output,
    review_static_guizang_html,
    run_guizang_validator,
)


def test_parse_validator_output_counts_pass_fail_warn():
    output = """
PASS xhs-01
WARN R4 body small
FAIL R1 overflow
"""

    status = parse_validator_output(output)

    assert status["pass_count"] == 1
    assert status["warn_count"] == 1
    assert status["fail_count"] == 1
    assert status["status"] == "fail"


def test_parse_validator_output_passes_with_warnings():
    output = """
PASS xhs-01
WARN R4 body small
"""

    status = parse_validator_output(output)

    assert status["status"] == "warn"


def test_review_static_guizang_html_requires_subject_map_for_image_overlay(tmp_path):
    (tmp_path / "index.html").write_text(
        '<section class="poster"><div class="image-hero"><h1>标题</h1></div></section>',
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path, mode="swiss")

    assert status["status"] == "fail"
    assert any("missing subject map" in line for line in status["lines"])


def test_review_static_guizang_html_accepts_subject_map_and_thumbnail_policy(tmp_path):
    (tmp_path / "index.html").write_text(
        """
        <section class="poster">
          <div class="image-hero"></div>
          <!-- subject map: safe text zone: lower-left
               thumbnail policy: verify 360px title readability.
          -->
        </section>
        """,
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path, mode="swiss")

    assert status["status"] == "pass"
    assert any("thumbnail policy note present" in line for line in status["lines"])


def test_review_static_guizang_html_rejects_banned_full_canvas_mask(tmp_path):
    (tmp_path / "index.html").write_text(
        """
        <section>
          <style>
            .hero::after{background:linear-gradient(180deg, rgba(0,0,0,.55), rgba(0,0,0,.1));}
          </style>
        </section>
        """,
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path)

    assert status["status"] == "fail"
    assert any("banned full-canvas black image mask" in line for line in status["lines"])


def test_review_static_guizang_html_rejects_duplicate_visible_copy(tmp_path):
    (tmp_path / "index.html").write_text(
        """
        <section class="poster" id="xhs-02">
          <h2>成本结构正在发生根本转移</h2>
          <p>成本结构正在发生根本转移</p>
        </section>
        """,
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path, mode="swiss")

    assert status["status"] == "fail"
    assert any("duplicated visible copy" in line for line in status["lines"])


def test_review_static_guizang_html_rejects_visible_scaffold_labels(tmp_path):
    (tmp_path / "index.html").write_text(
        """
        <section class="poster" id="xhs-03">
          <p>注记</p>
          <p>真实正文保留在这里。</p>
        </section>
        """,
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path, mode="swiss")

    assert status["status"] == "fail"
    assert any("scaffold label visible" in line for line in status["lines"])


def test_run_guizang_validator_records_failure_without_swallowing(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<section>No overlay</section>", encoding="utf-8")
    captured = {}

    def fake_run(args, check, capture_output, text, env):
        captured["env"] = env
        return subprocess.CompletedProcess(
            args,
            1,
            stdout="PASS xhs-01\nFAIL R1 overflow\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    status = run_guizang_validator(tmp_path, mode="editorial")

    assert status["status"] == "fail"
    assert status["fail_count"] == 1
    assert "FAIL R1 overflow" in status["stdout"]
    assert status["static_review"]["status"] == "pass"
    if Path(PROJECT_PLAYWRIGHT_BROWSERS).exists():
        assert captured["env"]["PLAYWRIGHT_BROWSERS_PATH"] == str(PROJECT_PLAYWRIGHT_BROWSERS)


def test_run_guizang_validator_skips_when_playwright_missing(tmp_path, monkeypatch):
    def fake_run(args, check, capture_output, text, env):
        return subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'playwright'",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    status = run_guizang_validator(tmp_path, mode="editorial")

    assert status["status"] == "skipped"
    assert "Guizang validator requires Node.js and Playwright" in status["reason"]


def test_run_guizang_validator_skips_when_browser_process_blocked(tmp_path, monkeypatch):
    def fake_run(args, check, capture_output, text, env):
        return subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="browserType.launch: Target page, context or browser has been closed\nkill EPERM\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    status = run_guizang_validator(tmp_path, mode="editorial")

    assert status["status"] == "skipped"
    assert "launch a browser process" in status["reason"]
