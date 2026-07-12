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


def _deep_rewrite_section(content: str) -> str:
    return _numbered_section(content, 2, r"深度改写|Deep Rewrite")


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


def _split_paragraphs(text: str) -> list[str]:
    """Split deep-rewrite text into clean paragraph strings.

    Treats both blank lines and inline '### ' / '## ' headings as separators.
    """
    if not text:
        return []
    paragraphs: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        if line.startswith("#") or line.startswith("**") and line.rstrip("*").endswith("**"):
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current).strip())
    return [p for p in paragraphs if p]


_CJK_RE = re.compile(r"[一-鿿]")
_STOP_TOKENS = {"的", "是", "在", "了", "和", "与", "或", "而", "为", "有"}


def _extract_keywords(title: str, max_keywords: int = 4) -> list[str]:
    """Extract distinctive CJK tokens from an insight title for paragraph matching."""
    seen: list[str] = []
    for char in title:
        if not _CJK_RE.match(char):
            continue
        if char in _STOP_TOKENS:
            continue
        if char in seen:
            continue
        seen.append(char)
        if len(seen) >= max_keywords:
            break
    return seen


def _score_paragraph(paragraph: str, keywords: list[str]) -> int:
    """Score a paragraph by keyword overlap with insight title."""
    if not keywords:
        return 0
    score = 0
    for kw in keywords:
        score += paragraph.count(kw)
    # Reward longer paragraphs a little so we don't always pick 1-sentence ones.
    score += min(len(paragraph) // 80, 3)
    return score


def _best_paragraph(paragraphs: list[str], keywords: list[str], used: set[int]) -> str:
    """Pick the first unused paragraph that shares keywords with the insight.

    Earlier paragraphs tend to introduce the topic of the first insight; later
    paragraphs typically expand on later insights. Picking the first matching
    paragraph preserves the rewritten narrative flow and avoids mismatches
    where a high-scoring later paragraph overrides an earlier, more relevant
    one for a different insight.
    """
    matches: list[tuple[int, int]] = []
    for i, paragraph in enumerate(paragraphs):
        if i in used:
            continue
        score = _score_paragraph(paragraph, keywords)
        if score > 0:
            matches.append((i, score))
    if not matches:
        return ""
    # Among matches, prefer the earliest paragraph with the highest score.
    matches.sort(key=lambda pair: (pair[0], -pair[1]))
    best_idx = matches[0][0]
    used.add(best_idx)
    return paragraphs[best_idx]


def _summarize_paragraph(text: str, max_chars: int = 90) -> str:
    """Trim a paragraph to a single sentence or N chars as a card body summary."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    # Prefer the first sentence that ends with terminal punctuation.
    for end in ("。", "！", "？"):
        idx = text.find(end)
        if 0 < idx < max_chars + 30:
            return text[: idx + 1].strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip("，,、;；") + "…"


def parse_insights(path: Path) -> list[dict]:
    content = _read(path)
    section = _core_insights_section(content)
    paragraphs = _split_paragraphs(_deep_rewrite_section(content))
    insights = []
    current = None
    used_paragraphs: set[int] = set()
    next_sequential = 0

    def _next_paragraph() -> str:
        nonlocal next_sequential
        if not paragraphs:
            return ""
        # Round-robin through paragraphs when keyword match fails.
        for _ in range(len(paragraphs)):
            idx = next_sequential % len(paragraphs)
            next_sequential += 1
            if idx in used_paragraphs:
                continue
            used_paragraphs.add(idx)
            return paragraphs[idx]
        return ""

    def flush_current() -> None:
        nonlocal current
        if not current:
            return
        text = " ".join(current["chunks"]).strip()
        title, inline_body = _split_title_body(text)
        if title:
            keywords = _extract_keywords(title)
            # Prefer keyword-matched paragraph; fall back to sequential round-robin.
            paragraph = _best_paragraph(paragraphs, keywords, used_paragraphs)
            if not paragraph:
                paragraph = _next_paragraph()
            body = inline_body.strip()
            if not body and paragraph:
                body = _summarize_paragraph(paragraph)
            elif paragraph and len(body) < 40:
                body = (body + " " + _summarize_paragraph(paragraph, max_chars=70)).strip()
            insights.append(
                {
                    "index": current["index"],
                    "title": title,
                    "body": body,
                    "one_liner": body[:80],
                    "keywords": keywords,
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

    # Final fallback: distribute any remaining unused paragraphs sequentially
    # so every insight gets a body explanation.
    for insight in insights:
        if insight["body"]:
            continue
        paragraph = _next_paragraph()
        if paragraph:
            insight["body"] = _summarize_paragraph(paragraph)

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
