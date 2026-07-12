from __future__ import annotations

import re
from html import unescape


def norm_text(text: str) -> str:
    return "".join(
        char
        for char in str(text or "")
        if char.strip() and char not in "，,。.!！?？；;：:、-—“”\"'（）()[]【】"
    )


def split_sentences(text: str, limit: int = 6) -> list[str]:
    clean = " ".join(str(text or "").split())
    if not clean:
        return []
    parts = []
    current = ""
    for char in clean:
        current += char
        if char in "。！？；;":
            parts.append(current.strip())
            current = ""
    if current.strip():
        parts.append(current.strip())
    if len(parts) <= 1 and "，" in clean:
        parts = [part.strip() for part in clean.split("，") if part.strip()]
    return parts[:limit]


def _is_duplicate(candidate: str, seen: set[str]) -> bool:
    norm = norm_text(candidate)
    if not norm:
        return True
    return norm in seen or any(norm in old or old in norm for old in seen)


def _push_unique(values: list[str], seen: set[str], value: str) -> None:
    clean = " ".join(str(value or "").split()).strip()
    if not clean or _is_duplicate(clean, seen):
        return
    seen.add(norm_text(clean))
    values.append(clean)


# Cover / lead / detail 字數上限（防渲染溢出）
HERO_MAX_CHARS = 12  # cover hero h1 允許中文字符數
LEAD_MAX_CHARS = 120  # hero_question / structure lead 段落
DETAIL_MAX_CHARS = 76  # density_panel / detail 條目
CAPTION_MAX_CHARS = 60
MIN_PAYLOAD_CHARS = 190
MIN_DETAIL_COUNT = 3
MIN_POINT_COUNT = 3


def _cap_chars(text: str, limit: int) -> str:
    """按中文字符數截斷（標點計入），保留尾部標點。"""
    clean = str(text or "").strip()
    if not clean or len(clean) <= limit:
        return clean
    return clean[:limit].rstrip("，,。.!！?？；;：:") + "…"


def build_copy_slots(page: dict) -> dict:
    title = str(page.get("title") or "").strip()
    body = str(page.get("body") or "").strip()
    subhead = str(page.get("subhead") or "").strip()
    pullquote = str(page.get("pullquote") or "").strip()
    point_values = [str(point or "").strip() for point in page.get("points") or []]
    detail_values = [str(point or "").strip() for point in page.get("details") or []]

    seen = {norm_text(title)} if norm_text(title) else set()
    if norm_text(pullquote):
        seen.add(norm_text(pullquote))
    unique_sentences: list[str] = []
    for sentence in [
        subhead,
        *point_values,
        *split_sentences(body, limit=6),
        *split_sentences(page.get("source_body", ""), limit=8),
    ]:
        _push_unique(unique_sentences, seen, sentence)

    lead = unique_sentences[0] if unique_sentences else body
    detail_seen = {norm_text(title)} if norm_text(title) else set()
    if norm_text(lead):
        detail_seen.add(norm_text(lead))
    details: list[str] = []
    for detail in [
        *detail_values,
        *unique_sentences[1:6],
        *split_sentences(page.get("source_body", ""), limit=8),
    ]:
        _push_unique(details, detail_seen, detail)
        if len(details) >= 5:
            break

    caption = ""
    for candidate in (pullquote, page.get("footer"), page.get("source_title")):
        candidate_text = str(candidate or "").strip()
        if candidate_text and not _is_duplicate(candidate_text, seen):
            caption = candidate_text
            seen.add(norm_text(candidate_text))
            break

    role = page.get("role", "")
    hero_cap = HERO_MAX_CHARS if role == "cover" else 40
    payload_chars = len(norm_text(" ".join([title, lead, *details, *point_values, pullquote])))
    point_count = len([point for point in point_values if norm_text(point)])
    detail_count = len(details)
    density_ok = role != "insight" or (
        payload_chars >= MIN_PAYLOAD_CHARS
        and detail_count >= MIN_DETAIL_COUNT
        and point_count >= MIN_POINT_COUNT
    )
    qa_flags = []
    if role == "insight" and not density_ok:
        if payload_chars < MIN_PAYLOAD_CHARS:
            qa_flags.append("low_payload")
        if detail_count < MIN_DETAIL_COUNT:
            qa_flags.append("few_details")
        if point_count < MIN_POINT_COUNT:
            qa_flags.append("few_points")
    return {
        "hero": _cap_chars(title, hero_cap),
        "lead": _cap_chars(lead, LEAD_MAX_CHARS),
        "details": [_cap_chars(d, DETAIL_MAX_CHARS) for d in details],
        "points": [_cap_chars(p, DETAIL_MAX_CHARS) for p in point_values[:6]],
        "sentences": unique_sentences[:6],
        "caption": _cap_chars(caption, CAPTION_MAX_CHARS),
        "meta": page.get("footer", ""),
        "payload_chars": payload_chars,
        "detail_count": detail_count,
        "point_count": point_count,
        "has_pullquote": bool(pullquote),
        "density_ok": density_ok,
        "qa_flags": qa_flags,
    }


def assign_copy_slots(page: dict) -> dict:
    enriched = dict(page)
    enriched["copy_slots"] = build_copy_slots(enriched)
    return enriched


def visible_text_nodes(html: str) -> list[str]:
    text = re.sub(r"<style\b.*?</style>", "", str(html or ""), flags=re.I | re.S)
    text = re.sub(r"<script\b.*?</script>", "", text, flags=re.I | re.S)
    nodes = []
    for raw in re.findall(r">([^<>]+)<", text):
        clean = " ".join(unescape(raw).split()).strip()
        if clean:
            nodes.append(clean)
    return nodes
