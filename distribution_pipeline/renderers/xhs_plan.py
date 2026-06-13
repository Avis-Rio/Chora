GROWTH_DEPTH_MAX_CARDS = 10


def _has_epilogue(epilogue: dict | None) -> bool:
    return bool(epilogue and epilogue.get("body"))


def _auto_card_count(insights: list[dict], epilogue: dict | None) -> int:
    return 1 + len(insights) + (1 if _has_epilogue(epilogue) else 0) + 1


def _growth_card_count(insights: list[dict], epilogue: dict | None) -> int:
    return min(_auto_card_count(insights, epilogue), GROWTH_DEPTH_MAX_CARDS)


def _split_sentences(text: str, limit: int = 3) -> list[str]:
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
    if len(parts) <= 1:
        parts = [clean]
    return parts[:limit]


def _strip_end_punctuation(text: str) -> str:
    return str(text or "").strip().rstrip("。.!！?？；;")


def _line_break(title: str, max_first: int = 12) -> list[str]:
    clean = _strip_end_punctuation(title)
    if not clean:
        return ["Chora"]
    for mark in ("，", "、", "：", "；", ",", ":", "|", "｜"):
        pos = clean.find(mark)
        if 3 <= pos <= max_first:
            first = clean[:pos].strip()
            second = clean[pos + 1 :].strip()
            return [first, second] if second else [first]
    if len(clean) <= 14:
        return [clean]
    return [clean[:max_first], clean[max_first: max_first + 14]]


def _cover_hook(source: dict, insights: list[dict]) -> tuple[str, list[str], str]:
    source_title = str(source.get("title", "") or "")
    joined = f"{source_title} {' '.join(item.get('title', '') for item in insights[:4])}"
    if ("Gemini" in joined and ("谷歌" in joined or "Google" in joined)) or "谷歌AI" in joined or "谷歌 AI" in joined:
        title = "谷歌 AI 慢了半拍，但还没输"
        return title, ["谷歌 AI 慢了半拍", "但还没输"], "先看几个反直觉判断：技术、组织、数据，哪一个才决定 Gemini 的翻身。"
    if any(word in joined.lower() for word in ("people disappear", "being alone", "solitude", "孤独", "孤寂", "独处")):
        title = "为什么越来越多人选择消失"
        return title, ["为什么越来越多人", "选择消失"], "不是不合群，而是现代生活正在让连接变得更难。"
    if any(word in joined.lower() for word in ("grow an audience", "followers", "0 followers", "粉丝", "受众")):
        title = "从零粉丝开始，增长靠的不是算法"
        return title, ["从零粉丝开始", "增长靠的不是算法"], "真正能拉动增长的杠杆只有两个：验证内容，真实社交。"
    if "Token" in joined or "成本" in joined:
        title = "AI 成本，正在重新分配权力"
        return title, ["AI 成本", "重新分配权力"], "看懂 Token，不只是看价格，而是看谁能定义计算的边界。"
    if insights:
        title = _strip_end_punctuation(insights[0].get("title", "")) or source_title
        return title, _line_break(title), "先看核心判断，再决定要不要读完整文章。"
    return source_title or "Chora", _line_break(source_title), "一组来自 Chora 的深度卡片。"


def _takeaway(insight: dict) -> str:
    body_sentences = _split_sentences(insight.get("body", ""), limit=2)
    if body_sentences:
        return body_sentences[0]
    title = _strip_end_punctuation(insight.get("title", ""))
    return f"真正要记住的是：{title}。" if title else ""


def _select_growth_insights(insights: list[dict], slots: int) -> list[dict]:
    if slots <= 0:
        return []
    if slots >= len(insights):
        return list(insights)
    if slots == 1:
        return [insights[0]]

    selected_offsets = [0]
    if len(insights) > 1 and slots >= 2:
        selected_offsets.append(1)
    tail_start = len(selected_offsets)
    remaining = slots - len(selected_offsets)
    tail = insights[tail_start:]
    if tail and remaining:
        if remaining == 1:
            selected_offsets.append(len(insights) - 1)
        else:
            for index in range(remaining):
                pos = round(index * (len(tail) - 1) / (remaining - 1))
                selected_offsets.append(tail_start + pos)

    unique = []
    for offset in selected_offsets:
        if offset not in unique:
            unique.append(offset)
    for offset in range(len(insights)):
        if len(unique) >= slots:
            break
        if offset not in unique:
            unique.append(offset)
    return [insights[offset] for offset in sorted(unique[:slots])]


def _closing_items(insights: list[dict], selected: list[dict]) -> list[dict]:
    source = selected or insights
    items = []
    for index, insight in enumerate(source[:3], start=1):
        items.append(
            {
                "index": f"{index:02d}",
                "title": _strip_end_punctuation(insight.get("title", "")),
                "note": _takeaway(insight),
            }
        )
    return items


def build_xhs_card_plan(
    source: dict,
    insights: list[dict],
    max_cards: int | None = None,
    epilogue: dict | None = None,
    strategy: str = "archive",
) -> list[dict]:
    if max_cards is None:
        max_cards = _growth_card_count(insights, epilogue) if strategy == "growth-depth" else _auto_card_count(insights, epilogue)
    if max_cards < 2:
        raise ValueError("max_cards must be at least 2")
    if strategy not in ("archive", "growth-depth"):
        raise ValueError(f"Unknown xhs card strategy: {strategy}")

    cover_title, cover_lines, cover_body = _cover_hook(source, insights) if strategy == "growth-depth" else (
        source.get("title", "Chora"),
        None,
        f"来源：{source.get('channel', 'Unknown')}",
    )

    cards = [
        {
            "type": "cover-poster",
            "title": cover_title,
            "title_lines": cover_lines,
            "body": cover_body,
            "index": 1,
            "strategy": strategy,
        }
    ]

    reserve_epilogue = _has_epilogue(epilogue) and max_cards >= 4
    slots_for_insights = max_cards - 2 - (1 if reserve_epilogue else 0)
    selected_insights = (
        _select_growth_insights(insights, slots_for_insights)
        if strategy == "growth-depth"
        else insights[:slots_for_insights]
    )

    for insight in selected_insights:
        cards.append(
            {
                "type": "single-insight",
                "title": insight.get("title", ""),
                "body": insight.get("body", ""),
                "index": len(cards) + 1,
                "insight_index": insight.get("index"),
                "reader_takeaway": _takeaway(insight),
                "strategy": strategy,
            }
        )

    if reserve_epilogue and len(cards) < max_cards - 1:
        cards.append(
            {
                "type": "philosophical-card",
                "title": epilogue.get("title", "哲思结语"),
                "body": epilogue.get("body", ""),
                "index": len(cards) + 1,
                "style": epilogue.get("style", ""),
                "strategy": strategy,
            }
        )

    omitted_count = max(len(insights) - len(selected_insights), 0)
    closing_title = "读完整篇前，先带走这三点" if strategy == "growth-depth" else "完整内容见 Chora"
    closing_body = (
        f"卡片保留核心判断，完整文章还收纳 {omitted_count} 个延伸洞察与上下文。"
        if strategy == "growth-depth" and omitted_count
        else "关注 Rhizomata，获取更多深度内容与延伸阅读。"
    )
    cards.append(
        {
            "type": "closing-card",
            "title": closing_title,
            "body": closing_body,
            "index": len(cards) + 1,
            "items": _closing_items(insights, selected_insights) if strategy == "growth-depth" else [],
            "strategy": strategy,
        }
    )
    return cards[:max_cards]
