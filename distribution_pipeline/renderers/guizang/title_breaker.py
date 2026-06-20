from __future__ import annotations

import re


END_PUNCT = "。.!！?？；;"
STRONG_MARKS = "，,、：:；;|｜—-"
SOFT_WORDS = (
    "不是",
    "而是",
    "为什么",
    "为何",
    "如何",
    "正在",
    "作为",
    "成为",
    "进入",
    "背后",
    "之中",
    "之后",
    "之前",
    "之下",
    "之间",
    "以及",
)
PREFERRED_SUFFIXES = (
    "陀思妥耶夫斯基",
    "Reverse Saidism",
    "DeepMind",
    "Google Brain",
    "OpenAI",
    "Transformer",
    "政治经济学",
    "现实主义",
    "历史性",
    "自主权",
    "大宗商品",
    "第三空间",
    "神经机制",
    "范式转移",
    "萨义德主义",
    "成本结构",
    "新形态",
    "文化史",
    "方法论",
    "经济学",
    "结构",
    "机制",
    "权力",
    "记忆",
    "身份",
    "空间",
    "算法",
    "模型",
    "成本",
    "孤独",
    "沉默",
    "陷阱",
    "系统",
)
PROTECTED_PHRASES = PREFERRED_SUFFIXES + (
    "小红书",
    "公众号",
    "Rhizomata",
    "Chora",
)


def strip_title_punctuation(text: str) -> str:
    return str(text or "").strip().rstrip(END_PUNCT)


def _normalize_lines(lines: list[str]) -> list[str]:
    return [" ".join(str(line or "").split()).strip() for line in lines if str(line or "").strip()]


def _split_structural(text: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    depth = 0
    for char in text:
        if char in "（(" and depth == 0 and current.strip():
            chunks.append(current.strip())
            current = ""
        current += char
        if char in "（(":
            depth += 1
        elif char in "）)" and depth:
            depth -= 1
            chunks.append(current.strip())
            current = ""
        elif depth == 0 and char in STRONG_MARKS:
            piece = current[:-1].strip()
            if piece:
                chunks.append(piece)
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text]


def _candidate_score(text: str, pos: int, target: int, min_tail: int) -> int:
    head = text[:pos]
    tail = text[pos:]
    score = abs(pos - target) * 8
    if len(head) < min_tail:
        score += 80
    if len(tail) < min_tail:
        score += 120
    if tail[:1] in "的之与和及、，,：:；;":
        score += 90
    if head[-1:] in "，,：:；;、":
        score -= 45
    for word in SOFT_WORDS:
        if head.endswith(word) or tail.startswith(word):
            score -= 28
    for phrase in PROTECTED_PHRASES:
        start = text.find(phrase)
        while start >= 0:
            end = start + len(phrase)
            if start < pos < end:
                score += 260
            start = text.find(phrase, start + 1)
    for word in PREFERRED_SUFFIXES:
        if head.endswith(word):
            score -= 38
        elif word in head[-len(word) - 2 : pos + len(word)]:
            score -= 12
    if re.search(r"[A-Za-z0-9]$", head) and re.match(r"^[A-Za-z0-9]", tail):
        score += 200
    return score


def _best_cut(text: str, target: int, min_tail: int) -> int:
    if len(text) <= target:
        return len(text)
    lower = max(min_tail, target - 5)
    upper = min(len(text) - min_tail, target + 5)
    if lower > upper:
        lower = min_tail
        upper = max(min_tail, len(text) - min_tail)
    candidates = range(lower, upper + 1)
    return min(candidates, key=lambda pos: _candidate_score(text, pos, target, min_tail))


def _split_long_chunk(text: str, target: int, min_tail: int) -> list[str]:
    if re.fullmatch(r"[（(][^（）()]+[）)]", text.strip()):
        return [text.strip()]
    rest = text
    parts: list[str] = []
    while len(rest) > target + min_tail:
        cut = _best_cut(rest, target, min_tail)
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        parts.append(rest)
    return parts


def _pack_chunks(chunks: list[str], target: int, min_tail: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for chunk in chunks:
        pieces = _split_long_chunk(chunk, target, min_tail) if len(chunk) > target + min_tail else [chunk]
        for piece in pieces:
            if not current:
                current = piece
                continue
            joined = f"{current}{piece}" if piece.startswith(("）", ")")) else f"{current}{piece}"
            spaced = f"{current} {piece}" if re.search(r"[A-Za-z0-9]$", current) and re.match(r"^[A-Za-z0-9]", piece) else joined
            if len(spaced) <= target + 2:
                current = spaced
            else:
                lines.append(current)
                current = piece
    if current:
        lines.append(current)
    return lines


def _rebalance(lines: list[str], min_tail: int, max_lines: int, target: int) -> list[str]:
    lines = _normalize_lines(lines)
    if len(lines) >= 2 and len(lines[-1]) < min_tail:
        merged = lines[-2] + lines[-1]
        recut = _split_long_chunk(merged, max(min_tail + 2, min(target, (len(merged) + 1) // 2)), min_tail)
        lines = lines[:-2] + recut
    while len(lines) > max_lines:
        tail = lines.pop()
        lines[-1] = lines[-1] + tail
        if len(lines[-1]) > target + min_tail and not re.search(r"[A-Za-z]", lines[-1]):
            merged = lines[-1]
            cut = _best_cut(merged, max(min_tail + 2, len(merged) // 2), min_tail)
            lines[-1:] = [merged[:cut].strip(), merged[cut:].strip()]
            if len(lines) > max_lines:
                lines[-2] = lines[-2] + lines[-1]
                lines.pop()
    if len(lines) >= 2 and len(lines[-1]) < min_tail:
        lines[-2] = lines[-2] + lines[-1]
        lines.pop()
    return _normalize_lines(lines)


def semantic_title_lines(
    title: str,
    target: int = 11,
    max_lines: int = 3,
    min_tail: int = 3,
) -> list[str]:
    raw = str(title or "").strip()
    terminal = raw[-1] if raw and raw[-1] in END_PUNCT else ""
    clean = strip_title_punctuation(raw)
    if not clean:
        return ["Chora"]
    explicit = _normalize_lines(clean.splitlines())
    if len(explicit) > 1:
        return _rebalance(explicit, min_tail=min_tail, max_lines=max_lines, target=target)
    chunks = _split_structural(clean)
    lines = _pack_chunks(chunks, target=target, min_tail=min_tail)
    lines = _rebalance(lines, min_tail=min_tail, max_lines=max_lines, target=target)
    if terminal and lines:
        lines[-1] = f"{lines[-1]}{terminal}"
    return lines
