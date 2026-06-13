import re
from pathlib import Path


def _read(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _numbered_section(content: str, number: int, title_pattern: str) -> str:
    match = re.search(
        rf"##\s*{number}\.\s*(?:{title_pattern}).*?\n(.*?)(?=\n##\s*\d+\.|\Z)",
        content,
        re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _core_insights_section(content: str) -> str:
    return _numbered_section(content, 3, r"核心洞察")


def _philosophical_epilogue_section(content: str) -> str:
    return _numbered_section(content, 4, r"哲思结语|Philosophical Epilogue")


def _split_title_body(text: str) -> tuple[str, str]:
    bold_match = re.match(r"\*\*(.+?)\*\*\s*[:：]\s*(.+)", text, re.DOTALL)
    if bold_match:
        return bold_match.group(1).strip(), bold_match.group(2).strip()

    bold_plain_match = re.match(r"\*\*(.+?)\*\*\s*(.+)?", text, re.DOTALL)
    if bold_plain_match:
        body = (bold_plain_match.group(2) or "").strip()
        body = re.sub(r"^[。.!！?？；;]+\s*", "", body)
        return bold_plain_match.group(1).strip(), body

    if "：" in text:
        title, body = text.split("：", 1)
        return title.strip(), body.strip()
    if ":" in text:
        title, body = text.split(":", 1)
        return title.strip(), body.strip()
    return text.strip(), ""


def parse_insights(path: Path) -> list[dict]:
    section = _core_insights_section(_read(path))
    insights = []
    current = None

    def flush_current() -> None:
        nonlocal current
        if not current:
            return
        text = " ".join(current["chunks"]).strip()
        title, body = _split_title_body(text)
        if title:
            insights.append(
                {
                    "index": current["index"],
                    "title": title,
                    "body": body,
                    "one_liner": body[:80],
                    "keywords": [],
                }
            )
        current = None

    for line in section.splitlines():
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^(?:[-*]\s+|(\d+)\.\s+)(.+)$", line)
        if match:
            flush_current()
            current = {
                "index": int(match.group(1) or len(insights) + 1),
                "chunks": [match.group(2).strip()],
            }
            continue

        if current:
            current["chunks"].append(line)

    flush_current()

    return insights


def parse_philosophical_epilogue(path: Path) -> dict:
    section = _philosophical_epilogue_section(_read(path))
    if not section:
        return {}

    style = ""
    lines = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("*") and line.endswith("*") and len(line) > 2:
            style = line.strip("*").strip()
            continue
        if line.startswith(">"):
            line = line.lstrip("> ").strip()
        lines.append(line)

    body = " ".join(lines).strip()
    if not body:
        return {}

    title = "哲思结语"
    sentences = re.split(r"(?<=[。！？])", body)
    for sentence in reversed([item.strip() for item in sentences if item.strip()]):
        if "时间" in sentence or "行动" in sentence:
            title = sentence.rstrip("。！？")
            break

    return {
        "title": title,
        "body": body,
        "style": style,
    }


def parse_tags(path: Path) -> list[str]:
    content = _read(path)
    match = re.search(r"(?:标签|Tags)[:：]\s*(.+)", content, re.IGNORECASE)
    if not match:
        return []
    return [tag.strip() for tag in re.split(r"[,，、]", match.group(1)) if tag.strip()]
