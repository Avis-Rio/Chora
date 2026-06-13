from __future__ import annotations

from html import unescape
import re


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


def build_copy_slots(page: dict) -> dict:
    title = str(page.get("title") or "").strip()
    body = str(page.get("body") or "").strip()
    point_values = [str(point or "").strip() for point in page.get("points") or []]
    sentences = point_values or split_sentences(body, limit=6)

    seen = {norm_text(title)} if norm_text(title) else set()
    unique_sentences: list[str] = []
    for sentence in sentences:
        _push_unique(unique_sentences, seen, sentence)

    lead = unique_sentences[0] if unique_sentences else body
    details = unique_sentences[1:5]

    caption = ""
    for candidate in (page.get("reader_takeaway"), page.get("footer"), page.get("source_title")):
        candidate_text = str(candidate or "").strip()
        if candidate_text and not _is_duplicate(candidate_text, seen):
            caption = candidate_text
            seen.add(norm_text(candidate_text))
            break

    return {
        "hero": title,
        "lead": lead,
        "details": details,
        "sentences": unique_sentences[:5],
        "caption": caption,
        "meta": page.get("footer", ""),
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
