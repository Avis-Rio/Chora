import subprocess
from pathlib import Path

from distribution_pipeline.renderers.guizang.validator import (
    _DEFAULT_PLAYWRIGHT_BROWSERS,
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


def test_review_static_guizang_html_rejects_visible_proxy_placeholders(tmp_path):
    (tmp_path / "index.html").write_text(
        """
        <section class="poster" id="xhs-04">
          <div data-metric-source="proxy">P01</div>
        </section>
        """,
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path, mode="swiss")

    assert status["status"] == "fail"
    assert any("proxy placeholder visible" in line for line in status["lines"])


def test_review_static_guizang_html_rejects_sparse_insight_payload(tmp_path):
    (tmp_path / "index.html").write_text(
        """
        <section class="poster role-insight" id="xhs-03">
          <h2>知识的重量</h2>
          <p>判断比执行重要。</p>
        </section>
        """,
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path, mode="editorial")

    assert status["status"] == "fail"
    assert any("insufficient visible payload" in line for line in status["lines"])


def test_review_static_guizang_html_rejects_workflow_density_failure(tmp_path):
    (tmp_path / "index.html").write_text(
        """
        <section class="poster role-insight" id="xhs-03" data-role="insight" data-density-ok="false" data-payload-chars="92" data-detail-count="1">
          <h2>知识的重量</h2>
          <p>判断比执行重要。收藏让知识变得可触摸。版本也保存阅读史。</p>
        </section>
        """,
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path, mode="editorial")

    assert status["status"] == "fail"
    assert any("workflow density gate failed" in line for line in status["lines"])
    assert any("workflow payload too sparse" in line for line in status["lines"])
    assert any("workflow detail count too low" in line for line in status["lines"])


def test_review_static_guizang_html_strict_blocks_qa_flags_and_missing_artifacts(tmp_path):
    (tmp_path / "index.html").write_text(
        """
        <section class="poster role-insight" id="xhs-03" data-role="insight" data-qa-flags="body_short" data-density-ok="true" data-payload-chars="180" data-detail-count="3">
          <h2>知识的重量</h2>
          <p>判断比执行重要。收藏让知识变得可触摸。版本也保存阅读史。阅读经验连接审美、材料、时间与思想。</p>
          <p>这些线索让书不再只是信息容器，而成为思想训练的现场。</p>
          <p>因此读者需要学习如何辨识版本、边注、纸张与翻译背后的文化秩序。</p>
        </section>
        """,
        encoding="utf-8",
    )

    status = review_static_guizang_html(tmp_path, mode="editorial", strict=True)

    assert status["status"] == "fail"
    assert any("workflow qa flags" in line for line in status["lines"])
    assert any("no exported PNG files" in line for line in status["lines"])
    assert any("no 360px thumbnail files" in line for line in status["lines"])


def test_run_guizang_validator_records_quality_gate(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<section>No overlay</section>", encoding="utf-8")

    def fake_run(args, check, capture_output, text, env):
        return subprocess.CompletedProcess(args, 0, stdout="PASS xhs-01\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    status = run_guizang_validator(tmp_path, mode="editorial")

    assert status["quality_gate"]["publishable"] is True


def test_run_guizang_validator_blocks_skipped_browser_when_required(tmp_path, monkeypatch):
    def fake_run(args, check, capture_output, text, env):
        return subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'playwright'",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    status = run_guizang_validator(tmp_path, mode="editorial", browser_required=True)

    assert status["status"] == "skipped"
    assert status["quality_gate"]["publishable"] is False
    assert any(reason["code"] == "R18" for reason in status["quality_gate"]["blocking_reasons"])


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
    expected_candidates = (*_DEFAULT_PLAYWRIGHT_BROWSERS, PROJECT_PLAYWRIGHT_BROWSERS)
    expected = next((candidate for candidate in expected_candidates if Path(candidate).exists()), None)
    if expected:
        assert captured["env"]["PLAYWRIGHT_BROWSERS_PATH"] == str(expected)


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


def test_run_guizang_validator_skips_when_playwright_browser_missing(tmp_path, monkeypatch):
    def fake_run(args, check, capture_output, text, env):
        return subprocess.CompletedProcess(
            args,
            1,
            stdout="",
            stderr="browserType.launch: Executable doesn't exist at /tmp/chrome\nLooks like Playwright was just installed or updated.",
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
