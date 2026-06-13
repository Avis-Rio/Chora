import re
from pathlib import Path


def _extract_section(content: str, heading: str) -> str:
    pattern = rf"##\s*{re.escape(heading)}\s*\n(.+?)(?=\n##|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_metadata(path: Path) -> dict:
    content = Path(path).read_text(encoding="utf-8")

    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    quotes_section = _extract_section(content, "金句")
    quotes = [
        re.sub(r"^[>\s＞]+", "", line).strip()
        for line in quotes_section.splitlines()
        if line.strip().startswith((">", "＞"))
    ]

    return {
        "title": title_match.group(1).strip() if title_match else "",
        "channel": _extract_section(content, "来源"),
        "source_url": _extract_section(content, "原始链接"),
        "publish_date": _extract_section(content, "发布时间"),
        "guests": _extract_section(content, "嘉宾"),
        "quotes": [quote for quote in quotes if quote],
    }
