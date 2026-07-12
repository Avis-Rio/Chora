from __future__ import annotations

import re

from distribution_pipeline.renderers.guizang.title_breaker import semantic_title_lines, strip_title_punctuation
from distribution_pipeline.renderers.guizang.title_budget import title_variants

FORBIDDEN_LINE_END = set("在与和的更不也是于中而及但代界性时、，：；")
FORBIDDEN_LINE_START = set("的了与和更中于而也及、，：；")
_CORE_TERMS = ("审美", "形塑", "知识", "价值", "文化", "阅读", "收藏", "传统", "经典", "书籍", "童书", "想象", "判断")
_PUNCT = "，,。.!！?？；;：:、-—“”\"'（）()[]【】《》"
MIN_PAYLOAD_CHARS = 190
MIN_POINT_COUNT = 3
MIN_DETAIL_COUNT = 3


def _norm_text(text: str) -> str:
    return "".join(char for char in str(text or "") if char.strip() and char not in _PUNCT)


def _sentences(text: str, limit: int = 4) -> list[str]:
    clean = " ".join(str(text or "").split())
    if not clean:
        return []
    parts: list[str] = []
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


def _cap_sentence(text: str, limit: int) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean or len(clean) <= limit:
        return clean
    return clean[:limit].rstrip(_PUNCT) + "。"


def _common_run(a: str, b: str, length: int = 8) -> bool:
    left = _norm_text(a)
    right = _norm_text(b)
    if not left or not right:
        return False
    if len(left) < length or len(right) < length:
        return left == right
    return any(left[i : i + length] in right for i in range(len(left) - length + 1))


def _polish_headline(text: str) -> str:
    head = strip_title_punctuation(str(text or "").strip()).strip(_PUNCT)
    if not head:
        return ""
    # Long possessive subjects usually make bad card headlines: keep the visual noun phrase.
    if "的" in head and len(head) > 8:
        suffix = head.rsplit("的", 1)[-1].strip(_PUNCT)
        if 4 <= len(suffix) <= 10:
            head = suffix
        elif len(suffix) < 4:
            prefix = head.rsplit("的", 1)[0].strip(_PUNCT)
            if 4 <= len(prefix) <= 10:
                head = prefix
    if head.startswith("在") and len(head) > 6:
        head = head[1:]
    while len(head) > 1 and head[-1] in FORBIDDEN_LINE_END:
        head = head[:-1].strip(_PUNCT)
    while len(head) > 1 and head[0] in FORBIDDEN_LINE_START:
        head = head[1:].strip(_PUNCT)
    if len(head) > 10:
        head = head[:10].rstrip("在与和的更不也是于中而虽但")
    return head or "Chora"


def _split_subhead(subhead: str, limit: int = 4) -> list[str]:
    """把较长 subhead 按“与 / 对 / 也 / 是 / 而”切分为可独立锚点的短语。"""
    if not subhead or len(subhead) <= 18:
        return [subhead] if subhead else []
    # 第一刀在原串上找分隔符，避免 stripped 后定位失效。
    seps = ("与", "对", "也", "是", "而", "或", "的")
    parts: list[str] = []
    used_positions: set[int] = set()
    for sep in seps:
        pos = subhead.find(sep)
        if 4 <= pos <= len(subhead) - 6 and pos not in used_positions:
            parts.append(subhead[: pos + len(sep)])
            parts.append(subhead[pos + len(sep) :])
            used_positions.add(pos)
            break
    if not parts:
        mid = len(subhead) // 2
        parts = [subhead[:mid], subhead[mid:]]
    # 清理标点（包括中英逗号），避免 _sentences 再次按逗号切分产生单字残片。
    cleaned: list[str] = []
    for p in parts:
        c = strip_title_punctuation(p)
        c = c.replace("，", "").replace(",", "").replace(" ", "")
        if 4 <= len(c) <= 24:
            cleaned.append(c)
    return cleaned[:limit]


def _split_headline(title: str) -> tuple[str, str]:
    clean = strip_title_punctuation(str(title or "").strip())
    if not clean:
        return "Chora", ""
    separators = ("不仅", "不是", "无法", "远胜", "更在", "形塑", "赋予", "丰富", "激发", "保持", "如", "是", "也", "而", "但", "并")
    for sep in separators:
        pos = clean.find(sep)
        if 3 <= pos <= 12:
            raw_head = clean[:pos].strip(_PUNCT)
            head = _polish_headline(raw_head)
            rest = clean[pos:].strip(_PUNCT)
            if 3 <= len(head) <= 12:
                return head, rest
    for mark in ("，", "：", "；", "、"):
        pos = clean.find(mark)
        if 4 <= pos <= 14:
            return _polish_headline(clean[:pos]), clean[pos + 1 :].strip(_PUNCT)
    if len(clean) <= 12:
        return _polish_headline(clean), ""
    variant = title_variants(clean, "M02")
    headline = _polish_headline(variant["display_title"])
    rest = clean[len(variant["display_title"]) :].strip(_PUNCT)
    return headline or _polish_headline(clean[:10]), rest


def _safe_lines(headline: str) -> list[str]:
    lines = semantic_title_lines(headline, target=7, max_lines=2, min_tail=3)[:2]
    fixed: list[str] = []
    for line in lines:
        clean = line.strip()
        while len(clean) > 1 and clean[-1] in FORBIDDEN_LINE_END:
            clean = clean[:-1].strip()
        while len(clean) > 1 and clean[0] in FORBIDDEN_LINE_START:
            clean = clean[1:].strip()
        fixed.append(clean)
    if len(fixed) == 2:
        joined = "".join(fixed)
        for term in _CORE_TERMS:
            pos = joined.find(term)
            if pos >= 0 and pos < len(fixed[0]) < pos + len(term):
                return [headline]
    return [line for line in fixed if line] or [headline]


def _unique_sentences(values: list[str], limit: int = 5) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        for sentence in _sentences(value, limit=8):
            clean = sentence.strip()
            norm = _norm_text(clean)
            if not clean or not norm:
                continue
            if norm in seen or any(norm in old or old in norm for old in seen):
                continue
            seen.add(norm)
            unique.append(clean)
            if len(unique) >= limit:
                return unique
    return unique


def _phrase_points(title: str, body: str, limit: int = 5) -> list[str]:
    """从长句中提取可做版面锚点的短语，避免卡片只有一段正文。"""
    text = strip_title_punctuation(" ".join([title, body]))
    chunks = [chunk.strip(_PUNCT + " ") for chunk in re.split(r"[，,。.!！?？；;：:、\s]+", text) if chunk.strip()]
    candidates: list[str] = []
    for chunk in chunks:
        if len(chunk) < 4:
            continue
        candidates.append(chunk)
    # 对长 chunk（>=24 字）再按“的/是/在/与”作次级切分，补足锚点。
    expanded: list[str] = []
    for chunk in candidates:
        if len(chunk) >= 24:
            for sep in ("的", "是", "在", "与", "对", "为", "而"):
                pos = chunk.find(sep)
                if 8 <= pos <= len(chunk) - 8:
                    left = chunk[: pos + len(sep)].strip(_PUNCT + " ")
                    right = chunk[pos + len(sep) :].strip(_PUNCT + " ")
                    # 拒收过短 / 过长的切片（避免 "也" / 1 字残片）。
                    if 8 <= len(left) <= 20:
                        expanded.append(left)
                    if 8 <= len(right) <= 20:
                        expanded.append(right)
                    break
    candidates.extend(expanded)
    # 最终再过滤：单字 / 纯虚词不应作为版面锚点。
    filtered = [c for c in candidates if len(c) >= 6 and not all(ch in "的也是在了与和对而或" for ch in c)]
    return _unique_sentences(filtered, limit=limit)


def _dedupe_near_overlap(phrases: list[str], window: int = 6) -> list[str]:
    """去除包含同一连续 N 字子串的近重复短语，避免 R11 重复可见文案。"""
    kept: list[str] = []
    signatures: list[str] = []
    for phrase in phrases:
        norm = _norm_text(phrase)
        if not norm:
            continue
        overlap = False
        for prev in signatures:
            for i in range(len(norm) - window + 1):
                token = norm[i : i + window]
                if token and token in prev:
                    overlap = True
                    break
            if overlap:
                break
        if overlap:
            continue
        kept.append(phrase)
        signatures.append(norm)
    return kept


def _qa_flags(payload_chars: int, points: list[str], details: list[str], pullquote: str) -> list[str]:
    flags: list[str] = []
    if payload_chars < MIN_PAYLOAD_CHARS:
        flags.append("low_payload")
    if len(points) < MIN_POINT_COUNT:
        flags.append("few_points")
    if len(details) < MIN_DETAIL_COUNT:
        flags.append("few_details")
    if not pullquote:
        flags.append("missing_pullquote")
    return flags


def _non_repeating(candidate: str, *against: str, length: int = 8) -> bool:
    return bool(candidate.strip()) and all(not _common_run(candidate, item, length) for item in against if item)


def _make_pullquote(title: str, raw_body: str, body: str, subhead: str, used: set[str] | None = None, body_parts: list[str] | None = None) -> str:
    used = used or set()
    body_parts = body_parts or []

    def _unused(candidate: str) -> bool:
        if not candidate or not _non_repeating(candidate, body, subhead, title, length=10):
            return False
        if any(_common_run(candidate, part, 8) for part in body_parts):
            return False
        norm = _norm_text(candidate)
        return bool(norm) and norm not in used

    title_clean = strip_title_punctuation(title)
    title_norm = _norm_text(title_clean)

    # 优先从 title 取 pullquote（不会侵占 body 给 points/details 的份额）。
    if 14 <= len(title_clean) <= 56 and title_norm not in used:
        if 18 <= len(title_clean) <= 56 and _non_repeating(title_clean, subhead, body, length=8):
            return _cap_sentence(title_clean, 72)
        # 在原 title（含标点）上找分隔符位置，避免 stripped 后找不到标点。
        for sep in ("，", "；", "、", "：", "。"):
            pos = title.find(sep)
            if 8 <= pos <= 40:
                tail = strip_title_punctuation(title[pos + 1 :])
                if 14 <= len(tail) <= 40 and _norm_text(tail) not in used and _non_repeating(tail, body, subhead, length=8):
                    return _cap_sentence(tail, 72)
                half = strip_title_punctuation(title[:pos])
                if 14 <= len(half) <= 40 and _norm_text(half) not in used and _non_repeating(half, body, subhead, length=8):
                    return _cap_sentence(half, 72)

    # 次选：body 中段或尾句（避开首句，保留给 points/details）。
    body_sentences = _sentences(raw_body, limit=8)
    for sentence in body_sentences[1:]:
        clean = _cap_sentence(sentence, 72)
        if 14 <= len(clean) <= 72 and _unused(clean):
            return clean

    for sentence in body_sentences[:1]:
        clean = _cap_sentence(sentence, 72)
        if 14 <= len(clean) <= 72 and _unused(clean):
            return clean

    # 兜底：拼接 2 个短 body 片段成 pullquote，避免直接用 subhead。
    if len(body_sentences) >= 2:
        for left, right in [(body_sentences[0], body_sentences[1]), (body_sentences[1], body_sentences[0])]:
            if len(left) >= 8 and len(right) >= 8 and len(right) <= 30:
                candidate = f"{left.strip(_PUNCT)}，{right.strip(_PUNCT)}"
                if 18 <= len(candidate) <= 72 and _unused(candidate):
                    return _cap_sentence(candidate, 72)

    title_clean = strip_title_punctuation(title)
    title_norm = _norm_text(title_clean)
    if 14 <= len(title_clean) <= 56 and title_norm not in used:
        # 优先完整短标题作为 pullquote，但必须与 subhead/body 不重叠。
        if 18 <= len(title_clean) <= 56 and _non_repeating(title_clean, subhead, body, length=8):
            return _cap_sentence(title_clean, 72)
        # 含分隔的长标题：取后半句（多为判断/转折，信息更密）。
        for sep in ("，", "；", "、", "："):
            pos = title_clean.find(sep)
            if 8 <= pos <= 40:
                tail = title_clean[pos + 1 :].strip(_PUNCT)
                if 14 <= len(tail) <= 40 and _norm_text(tail) not in used and _non_repeating(tail, body, subhead, length=8):
                    return _cap_sentence(tail, 72)
                half = title_clean[:pos].strip(_PUNCT)
                if 14 <= len(half) <= 40 and _norm_text(half) not in used and _non_repeating(half, body, subhead, length=8):
                    return _cap_sentence(half, 72)
        if 18 <= len(title_clean) <= 56 and _norm_text(title_clean) not in used and _non_repeating(title_clean, subhead, body, length=8):
            return _cap_sentence(title_clean, 72)

    core = _polish_headline(title_clean) or "阅读"
    core_norm = _norm_text(core)
    core_candidates = [core]
    if title_clean and len(title_clean) >= 8:
        tail = title_clean[-6:].strip(_PUNCT)
        if 3 <= len(tail) <= 8 and tail not in core_candidates:
            core_candidates.append(tail)
    templates = [
        "对{core}而言，更深的提问在于它如何改变了我们看事物的方式。",
        "理解{core}之后，最难的是在日常里守住它带来的尺度。",
        "若只记住{core}的一个面向，应是它把经验重新打开的能力。",
        "关于{core}，最值得保留的不是结论，而是它让人重新追问的位置。",
        "把{core}放进生活，考验的不是知识，而是判断与耐心。",
    ]
    for candidate in core_candidates:
        for template in templates:
            filled = template.format(core=candidate)
            if _unused(filled):
                return _cap_sentence(filled, 72)
    return _cap_sentence(title_clean, 72) if title_clean else ""


def _layout_intent(title: str, body: str) -> str:
    text = f"{title} {body}"
    if any(word in text for word in ("价值", "文化", "审美", "收藏", "书籍")):
        return "object-culture"
    if any(word in text for word in ("无法", "不是", "远胜", "反对")):
        return "argument"
    if any(word in text for word in ("想象", "精神", "阅读")):
        return "inner-life"
    return "insight"


def _recipe_hint(intent: str) -> str:
    return {
        "object-culture": "M02",
        "argument": "M05",
        "inner-life": "M11",
        "insight": "M03",
    }.get(intent, "M03")


def build_card_copies(source: dict, insights: list[dict], epilogue: dict | None = None, visual_briefs: list[dict] | None = None) -> list[dict]:
    copies: list[dict] = []
    used_pullquotes: set[str] = set()
    for offset, insight in enumerate(insights, start=1):
        raw_title = str(insight.get("title") or "").strip()
        raw_body = str(insight.get("body") or "").strip()
        headline, remainder = _split_headline(raw_title)
        body_sentences = _sentences(raw_body, limit=8)
        subhead = remainder or (body_sentences[0] if body_sentences else "")
        body_parts = [sentence for sentence in body_sentences if not _common_run(sentence, subhead, 8)]
        body = " ".join(body_parts[:6]) or raw_body or subhead
        body = _cap_sentence(body, 360)
        subhead = _cap_sentence(subhead, 96)
        point_pool = _unique_sentences([subhead, body, raw_body, raw_title], limit=7)
        phrase_pool = _phrase_points(raw_title, raw_body, limit=12)
        pullquote = _make_pullquote(raw_title, raw_body, body, subhead, used=used_pullquotes, body_parts=body_parts)
        if pullquote:
            used_pullquotes.add(_norm_text(pullquote))
        body_sentences = [s for s in _sentences(body, limit=8) if _non_repeating(s, headline, length=4) and _non_repeating(s, subhead, length=4)]
        raw_body_sentences = [s for s in _sentences(raw_body, limit=8) if _non_repeating(s, headline, length=4) and _non_repeating(s, subhead, length=4)]
        subhead_fragments = [s for s in _split_subhead(subhead) if _non_repeating(s, headline, length=4) and _non_repeating(s, pullquote, length=8)]
        # 若 subhead 已被拆为多片，候选中用碎片替掉完整 subhead，避免 dedupe 把碎片吃掉。
        subhead_for_pool = subhead_fragments if len(subhead_fragments) >= 2 else [subhead]
        # Allow small overlap with pullquote (4 chars) so adjacent sentences survive dedupe.
        points = _dedupe_near_overlap(
            [p for p in _unique_sentences([*subhead_for_pool, *phrase_pool, *body_sentences, *raw_body_sentences], limit=24)
             if _non_repeating(p, headline, length=4) and _non_repeating(p, pullquote, length=8)],
            window=4,
        )[:6]
        detail_pool = [item for item in _unique_sentences([raw_body, raw_title, *phrase_pool, *raw_body_sentences, *body_sentences], limit=18)
                       if _non_repeating(item, subhead, length=10) and _non_repeating(item, pullquote, length=8) and _non_repeating(item, headline, length=4)]
        # 追加 subhead 碎片作为细节锚点（碎片天然与 subhead 重叠，但不应被原 filter 误杀）。
        if subhead_fragments:
            detail_pool.extend([f for f in subhead_fragments if f not in detail_pool])
        details = _dedupe_near_overlap(detail_pool, window=6)[:6]
        payload_chars = len(_norm_text(" ".join([headline, subhead, body, pullquote, *points, *details])))
        qa_flags = _qa_flags(payload_chars, points, details, pullquote)
        density = "high" if payload_chars >= 260 and len(details) >= 4 else "medium" if payload_chars >= MIN_PAYLOAD_CHARS and len(details) >= MIN_DETAIL_COUNT else "low"
        intent = _layout_intent(raw_title, raw_body)
        copies.append(
            {
                "insight_index": insight.get("index") or offset,
                "source_title": raw_title,
                "source_body": raw_body,
                "headline": headline,
                "headline_lines": _safe_lines(headline),
                "subhead": subhead,
                "body": body,
                "points": points,
                "details": details,
                "pullquote": pullquote,
                "copy_density": density,
                "min_payload_ok": not qa_flags,
                "qa_flags": qa_flags,
                "payload_chars": payload_chars,
                "image_prompt": f"{headline}, editorial magazine image, warm texture",
                "layout_intent": intent,
                "recipe_hint": _recipe_hint(intent),
            }
        )
    return copies
