import os
import re
import subprocess
from pathlib import Path
from typing import Any

from distribution_pipeline.renderers.guizang.content_allocator import norm_text, visible_text_nodes
from distribution_pipeline.renderers.guizang.template_loader import vendor_path

DEPENDENCY_REASON = "Guizang validator requires Node.js and Playwright."
SANDBOX_REASON = "Guizang validator requires permission to launch a browser process."
PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROJECT_PLAYWRIGHT_BROWSERS = PROJECT_ROOT / ".ms-playwright"
_DEFAULT_PLAYWRIGHT_BROWSERS = (
    Path.home() / "Library" / "Caches" / "ms-playwright",
    Path.home() / ".cache" / "ms-playwright",
)
SCAFFOLD_LABELS = {"注记", "脉络", "张力", "信号", "判断", "余波", "边界", "后果"}


def _poster_sections(markup: str) -> list[tuple[str, str]]:
    matches = list(
        re.finditer(r"<section\b(?P<attrs>[^>]*)>(?P<body>.*?)</section>", markup, flags=re.I | re.S)
    )
    if not matches:
        return [("document", markup)]

    sections = []
    for index, match in enumerate(matches, start=1):
        attrs = match.group("attrs") or ""
        class_match = re.search(r'\bclass=["\']([^"\']+)["\']', attrs, flags=re.I)
        if class_match and "poster" not in class_match.group(1).split():
            continue
        id_match = re.search(r'\bid=["\']([^"\']+)["\']', attrs, flags=re.I)
        section_id = id_match.group(1) if id_match else f"poster-{index:02d}"
        sections.append((section_id, match.group(0)))

    if sections:
        return sections
    return [(f"section-{index:02d}", match.group(0)) for index, match in enumerate(matches, start=1)]


def _copy_duplicate_lines(markup: str) -> list[str]:
    lines = []
    for section_id, section in _poster_sections(markup):
        seen: list[tuple[str, str]] = []
        for node in visible_text_nodes(section):
            normalized = norm_text(node)
            if len(normalized) < 12:
                continue
            duplicate = next(
                (
                    original
                    for original, old in seen
                    if normalized == old
                    or (len(normalized) >= 18 and normalized in old)
                    or (len(old) >= 18 and old in normalized)
                ),
                None,
            )
            if duplicate:
                sample = node[:34]
                lines.append(f"FAIL R11 duplicated visible copy in {section_id}: {sample}")
                break
            seen.append((node, normalized))
    if not lines:
        lines.append("PASS R11 no duplicated visible copy inside a card")
    return lines


def _scaffold_label_lines(markup: str) -> list[str]:
    hits = []
    label_norms = {norm_text(label) for label in SCAFFOLD_LABELS}
    for section_id, section in _poster_sections(markup):
        for node in visible_text_nodes(section):
            if norm_text(node) in label_norms:
                hits.append(f"FAIL R12 scaffold label visible in {section_id}: {node}")
                break
    return hits or ["PASS R12 no scaffold label injection visible"]


def _proxy_placeholder_lines(markup: str) -> list[str]:
    hits = []
    placeholder = re.compile(r"^P\d{2}$")
    for section_id, section in _poster_sections(markup):
        for node in visible_text_nodes(section):
            if placeholder.match(norm_text(node)):
                hits.append(f"FAIL R14 proxy placeholder visible in {section_id}: {node}")
                break
    return hits or ["PASS R14 no visible proxy placeholders"]


def _attr(section: str, name: str) -> str:
    match = re.search(rf'\b{name}=["\']([^"\']*)["\']', section, flags=re.I)
    return match.group(1).strip() if match else ""


def _payload_density_lines(markup: str) -> list[str]:
    lines = []
    for section_id, section in _poster_sections(markup):
        if "role-insight" not in section and 'data-role="insight"' not in section:
            continue
        nodes = [
            node
            for node in visible_text_nodes(section)
            if norm_text(node) not in {norm_text(label) for label in SCAFFOLD_LABELS}
        ]
        payload = norm_text("".join(nodes))
        semantic_blocks = len([node for node in nodes if len(norm_text(node)) >= 8])
        if len(payload) < 120 or semantic_blocks < 3:
            lines.append(
                f"FAIL R15 insufficient visible payload in {section_id}: chars={len(payload)} blocks={semantic_blocks}"
            )
    return lines or ["PASS R15 insight cards carry enough visible payload"]


def _workflow_contract_lines(markup: str, strict: bool = False) -> list[str]:
    lines = []
    for section_id, section in _poster_sections(markup):
        role = _attr(section, "data-role")
        recipe = _attr(section, "data-recipe")
        qa_flags = [flag for flag in _attr(section, "data-qa-flags").split() if flag]
        density_ok = _attr(section, "data-density-ok").lower()
        payload_raw = _attr(section, "data-payload-chars")
        detail_raw = _attr(section, "data-detail-count")
        try:
            payload_chars = int(payload_raw) if payload_raw else None
        except ValueError:
            payload_chars = None
        try:
            detail_count = int(detail_raw) if detail_raw else None
        except ValueError:
            detail_count = None

        if role == "insight":
            if density_ok == "false":
                lines.append(f"FAIL R16 workflow density gate failed in {section_id}: density_ok=false")
            if payload_chars is not None and payload_chars < 120:
                lines.append(f"FAIL R16 workflow payload too sparse in {section_id}: chars={payload_chars}")
            if detail_count is not None and detail_count < 2:
                lines.append(
                    f"FAIL R16 workflow detail count too low in {section_id}: details={detail_count}"
                )
        if qa_flags:
            severity = "FAIL" if strict else "WARN"
            lines.append(f"{severity} R16 workflow qa flags in {section_id}: {','.join(qa_flags)}")
        if recipe in {"M16", "S08"} and "subject map:" not in section:
            lines.append(
                f"FAIL R16 text-on-image recipe lacks local subject map in {section_id}: recipe={recipe}"
            )
    return lines or ["PASS R16 workflow copy/planner contract satisfied"]


def _output_artifact_lines(target_dir: Path, strict: bool = False) -> list[str]:
    target_dir = Path(target_dir)
    output_dir = target_dir / "output"
    pngs = sorted(output_dir.glob("*.png")) if output_dir.exists() else []
    thumbnails = (
        sorted((output_dir / "thumbnails").glob("*.png")) if (output_dir / "thumbnails").exists() else []
    )
    if not strict:
        return ["PASS R17 strict artifact gate not requested"]
    lines = []
    if not pngs:
        lines.append("FAIL R17 no exported PNG files found")
    if target_dir.name == "xhs" and len(pngs) < 8:
        lines.append(f"FAIL R17 insufficient XHS PNG exports: count={len(pngs)}")
    if not thumbnails:
        lines.append("FAIL R17 no 360px thumbnail files found")
    if not lines:
        lines.append(
            f"PASS R17 exported PNG and thumbnail artifacts present: png={len(pngs)} thumbnails={len(thumbnails)}"
        )
    return lines


def review_static_guizang_html(target_dir: Path, mode: str = "editorial", strict: bool = False) -> dict:
    html_path = Path(target_dir) / "index.html"
    if not html_path.exists():
        return {
            "status": "warn",
            "pass_count": 0,
            "warn_count": 1,
            "fail_count": 0,
            "lines": ["WARN R8 static QA skipped: index.html not found"],
        }

    html = html_path.read_text(encoding="utf-8")
    markup = re.sub(r"<style\b.*?</style>", "", html, flags=re.I | re.S)
    markup = re.sub(r"<script\b.*?</script>", "", markup, flags=re.I | re.S)
    lines = []
    has_text_on_image = "hero-bleed" in markup or "image-hero" in markup
    if has_text_on_image:
        if "subject map:" not in html:
            lines.append("FAIL R8 text-on-image block is missing subject map")
        else:
            lines.append("PASS R8 text-on-image subject map present")
        if "thumbnail policy:" not in html:
            lines.append("WARN R9 text-on-image block is missing thumbnail policy note")
        else:
            lines.append("PASS R9 thumbnail policy note present")
    else:
        lines.append("PASS R8 no text-on-image block detected")

    banned_full_canvas_mask = re.search(
        r"linear-gradient\(\s*180deg\s*,\s*rgba\(\s*0\s*,\s*0\s*,\s*0",
        html,
        flags=re.I,
    )
    if banned_full_canvas_mask:
        lines.append("FAIL R10 banned full-canvas black image mask detected")
    else:
        lines.append("PASS R10 no banned full-canvas black image mask")

    lines.extend(_copy_duplicate_lines(markup))
    lines.extend(_scaffold_label_lines(markup))
    lines.extend(_payload_density_lines(markup))
    lines.extend(_workflow_contract_lines(markup, strict=strict))
    lines.extend(_output_artifact_lines(target_dir, strict=strict))

    if mode == "swiss" and 'data-metric-source="proxy"' in markup:
        lines.append(
            "FAIL R13 Swiss proxy metric scales are not publishable in strict mode"
            if strict
            else "PASS R13 Swiss proxy metric scales are explicitly labelled"
        )
    if mode == "swiss":
        lines.extend(_proxy_placeholder_lines(markup))

    status = parse_validator_output("\n".join(lines))
    return status


def parse_validator_output(output: str) -> dict:
    lines = [line.strip() for line in str(output or "").splitlines() if line.strip()]
    pass_count = sum(1 for line in lines if line.startswith("PASS"))
    warn_count = sum(1 for line in lines if line.startswith("WARN"))
    fail_count = sum(1 for line in lines if line.startswith("FAIL"))
    if fail_count:
        status = "fail"
    elif warn_count:
        status = "warn"
    else:
        status = "pass"
    return {
        "status": status,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "lines": lines,
    }


def _merge_validator_status(
    browser_status: dict, static_status: dict, strict: bool = False, browser_required: bool = False
) -> dict:
    merged = dict(browser_status)
    merged["pass_count"] = browser_status.get("pass_count", 0) + static_status.get("pass_count", 0)
    merged["warn_count"] = browser_status.get("warn_count", 0) + static_status.get("warn_count", 0)
    merged["fail_count"] = browser_status.get("fail_count", 0) + static_status.get("fail_count", 0)
    merged["lines"] = [*browser_status.get("lines", []), *static_status.get("lines", [])]
    if merged["fail_count"]:
        merged["status"] = "fail"
    elif merged["warn_count"]:
        merged["status"] = "warn"
    else:
        merged["status"] = "pass"
    merged["static_review"] = static_status
    merged["quality_gate"] = quality_gate_from_review(
        merged, strict=strict, browser_required=browser_required
    )
    return merged


def _is_missing_playwright(text: str) -> bool:
    return (
        "ERR_MODULE_NOT_FOUND" in text
        or "Cannot find package 'playwright'" in text
        or "Cannot find module 'playwright'" in text
        or "Executable doesn't exist" in text
        or "Looks like Playwright was just installed or updated" in text
    )


def _is_browser_process_blocked(text: str) -> bool:
    return (
        "kill EPERM" in text
        or "SIGABRT" in text
        or "Target page, context or browser has been closed" in text
        or "Chrome CDP endpoint was not ready" in text
    )


def _node_env() -> dict[str, str]:
    env = os.environ.copy()
    paths = [str(path / "node_modules") for path in [PROJECT_ROOT, *PROJECT_ROOT.parents]]
    if env.get("NODE_PATH"):
        paths.append(env["NODE_PATH"])
    env["NODE_PATH"] = os.pathsep.join(paths)
    if "PLAYWRIGHT_BROWSERS_PATH" not in env:
        for candidate in (*_DEFAULT_PLAYWRIGHT_BROWSERS, PROJECT_PLAYWRIGHT_BROWSERS):
            if candidate.is_dir():
                env["PLAYWRIGHT_BROWSERS_PATH"] = str(candidate)
                break
    return env


def quality_gate_from_review(
    review: dict[str, Any], strict: bool = False, browser_required: bool = False
) -> dict:
    reasons = []
    status = review.get("status", "unknown")
    if status == "skipped" and browser_required:
        reasons.append(
            {
                "code": "R18",
                "severity": "fail",
                "layer": "validator_env",
                "message": review.get("reason") or "browser validator skipped",
            }
        )
    if review.get("fail_count", 0) > 0:
        reasons.append(
            {
                "code": "R0",
                "severity": "fail",
                "layer": "validator",
                "message": f"validator reported {review.get('fail_count')} failures",
            }
        )
    if strict and review.get("warn_count", 0) > 0:
        reasons.append(
            {
                "code": "R0",
                "severity": "fail",
                "layer": "validator",
                "message": f"strict mode blocks {review.get('warn_count')} warnings",
            }
        )
    publishable = not reasons and status == "pass"
    return {
        "strict": bool(strict),
        "browser_required": bool(browser_required),
        "publishable": publishable,
        "status": "pass" if publishable else "fail",
        "blocking_reasons": reasons,
    }


def run_guizang_validator(
    target_dir: Path, mode: str = "editorial", strict: bool = False, browser_required: bool = False
) -> dict:
    script = vendor_path("validate-social-deck.mjs")
    args = ["node", str(script), str(Path(target_dir)), f"--style={mode}"]
    static_status = review_static_guizang_html(target_dir, mode=mode, strict=strict)
    try:
        result = subprocess.run(args, check=False, capture_output=True, text=True, env=_node_env())
    except FileNotFoundError:
        skipped = {"status": "skipped", "reason": DEPENDENCY_REASON, "static_review": static_status}
        skipped["quality_gate"] = quality_gate_from_review(
            skipped, strict=strict, browser_required=browser_required
        )
        return skipped

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    combined = "\n".join(part for part in [stdout, stderr] if part)
    if _is_missing_playwright(combined):
        skipped = {
            "status": "skipped",
            "reason": DEPENDENCY_REASON,
            "static_review": static_status,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }
        skipped["quality_gate"] = quality_gate_from_review(
            skipped, strict=strict, browser_required=browser_required
        )
        return skipped
    if _is_browser_process_blocked(combined):
        skipped = {
            "status": "skipped",
            "reason": SANDBOX_REASON,
            "static_review": static_status,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }
        skipped["quality_gate"] = quality_gate_from_review(
            skipped, strict=strict, browser_required=browser_required
        )
        return skipped

    status = parse_validator_output(combined)
    if result.returncode != 0 and status["fail_count"] == 0:
        status["status"] = "fail"
        status["fail_count"] = 1
        status["lines"].append(f"FAIL validator exited with code {result.returncode}")
    status.update(
        {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }
    )
    return _merge_validator_status(status, static_status, strict=strict, browser_required=browser_required)
