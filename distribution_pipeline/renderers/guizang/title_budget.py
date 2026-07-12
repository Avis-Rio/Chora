from __future__ import annotations

import re
from dataclasses import dataclass

from distribution_pipeline.renderers.guizang.title_breaker import semantic_title_lines, strip_title_punctuation


@dataclass(frozen=True)
class TitleBudget:
    """Recipe-level headline budget for small-screen social cards."""

    max_lines: int = 2
    line_chars: int = 9
    max_chars: int = 18
    min_tail: int = 3
    font_px: int | None = None


DEFAULT_BUDGET = TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=76)

TITLE_BUDGETS: dict[str, TitleBudget] = {
    # Editorial
    "M01": TitleBudget(max_lines=3, line_chars=12, max_chars=36, font_px=62),
    "M02": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=76),
    "M03": TitleBudget(max_lines=3, line_chars=8, max_chars=24, font_px=72),
    "M05": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=76),
    "M06": TitleBudget(max_lines=2, line_chars=10, max_chars=20, font_px=72),
    "M07": TitleBudget(max_lines=2, line_chars=10, max_chars=20, font_px=78),
    "M08": TitleBudget(max_lines=3, line_chars=8, max_chars=24, font_px=70),
    "M09": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=76),
    "M10": TitleBudget(max_lines=2, line_chars=10, max_chars=20, font_px=72),
    "M11": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=76),
    "M13": TitleBudget(max_lines=2, line_chars=12, max_chars=24, font_px=104),
    "M14": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=74),
    "M15": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=76),
    "M16": TitleBudget(max_lines=3, line_chars=10, max_chars=30, font_px=60),
    # Swiss
    "S01": TitleBudget(max_lines=3, line_chars=10, max_chars=30, font_px=64),
    "S02": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=72),
    "S03": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=72),
    "S04": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=72),
    "S05": TitleBudget(max_lines=2, line_chars=10, max_chars=20, font_px=70),
    "S06": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=72),
    "S07": TitleBudget(max_lines=2, line_chars=10, max_chars=20, font_px=72),
    "S08": TitleBudget(max_lines=3, line_chars=10, max_chars=30, font_px=60),
    "S09": TitleBudget(max_lines=2, line_chars=8, max_chars=16, font_px=68),
    "S10": TitleBudget(max_lines=2, line_chars=8, max_chars=16, font_px=68),
    "S11": TitleBudget(max_lines=2, line_chars=9, max_chars=18, font_px=70),
    "S12": TitleBudget(max_lines=2, line_chars=8, max_chars=16, font_px=66),
    "S13": TitleBudget(max_lines=2, line_chars=8, max_chars=16, font_px=66),
}

_STOP_WORDS = {
    "一个", "一种", "那些", "这个", "这场", "这种", "通过", "关于", "因为", "但是", "如果", "以及", "并且", "我们", "他们",
    "真正", "其实", "正在", "可以", "不是", "就是", "成为", "来自", "对于", "之间", "之中", "之下", "背后",
}
_CONNECTORS = "，,。；;：:、———-｜|（）()《》“”\"'！？!?"


def title_budget_for(recipe: str | None) -> TitleBudget:
    return TITLE_BUDGETS.get(str(recipe or ""), DEFAULT_BUDGET)


def _tokens(text: str) -> list[str]:
    raw = strip_title_punctuation(str(text or "").strip())
    if not raw:
        return []
    parts = re.split(f"[{re.escape(_CONNECTORS)}\\s]+", raw)
    tokens: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Prefer compact semantic chunks around particles; keeps nouns/metrics.
        sub = re.split(r"(?<=[的与和及在为是])", part)
        for item in sub:
            item = item.strip()
            if item and item not in _STOP_WORDS:
                tokens.append(item)
    return tokens or [raw]


def shorten_title(text: str, max_chars: int) -> str:
    """Create a display headline by preserving front-loaded meaning under budget."""
    original = str(text or "").strip()
    terminal = original[-1] if original and original[-1] in "。！？!?" else ""
    raw = strip_title_punctuation(original)
    if len(raw) <= max_chars:
        return f"{raw}{terminal}" if terminal and len(raw) + 1 <= max_chars + 1 else raw
    tokens = _tokens(raw)
    chosen: list[str] = []
    for token in tokens:
        candidate = "".join([*chosen, token])
        if len(candidate) <= max_chars:
            chosen.append(token)
        elif not chosen and len(token) > max_chars:
            compact = token[:max_chars]
            return f"{compact}{terminal}" if terminal and len(compact) < max_chars else compact
        if len("".join(chosen)) >= max_chars - 2:
            break
    compact = "".join(chosen).strip()
    if len(compact) >= max(4, min(max_chars, 8)):
        compact = compact[:max_chars]
        return f"{compact}{terminal}" if terminal and len(compact) < max_chars else compact
    # Fallback: take the first meaningful budget instead of adding ellipsis.
    compact = raw[:max_chars]
    return f"{compact}{terminal}" if terminal and len(compact) < max_chars else compact


def title_variants(title: str, recipe: str | None = None) -> dict:
    budget = title_budget_for(recipe)
    display = shorten_title(title, budget.max_chars)
    short = shorten_title(display, min(10, max(6, budget.line_chars)))
    lines = semantic_title_lines(display, target=budget.line_chars, max_lines=budget.max_lines, min_tail=budget.min_tail)
    # If semantic packing still exceeds budget after rebalancing, shorten once more.
    if len(lines) > budget.max_lines or any(len(line) > budget.line_chars + 2 for line in lines):
        display = shorten_title(display, max(6, budget.line_chars * budget.max_lines - 2))
        lines = semantic_title_lines(display, target=budget.line_chars, max_lines=budget.max_lines, min_tail=budget.min_tail)
    return {
        "source_title": str(title or ""),
        "display_title": display,
        "short_title": short,
        "title_lines": lines[: budget.max_lines],
        "title_budget": {
            "max_lines": budget.max_lines,
            "line_chars": budget.line_chars,
            "max_chars": budget.max_chars,
            "font_px": budget.font_px,
        },
    }
