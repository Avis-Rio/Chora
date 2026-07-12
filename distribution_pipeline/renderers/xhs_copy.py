from __future__ import annotations

import re

DEFAULT_CHORA_URL = "https://chora.avisionary.top"
DEFAULT_BRAND = {
    "chora_url": DEFAULT_CHORA_URL,
    "rhizomata_name": "Rhizomata",
}

TAG_ALIASES = {
    "technology": "科技",
    "tech": "科技",
    "economics": "商业思考",
    "economy": "商业思考",
    "business": "商业思考",
    "business model": "商业模式",
    "power & politics": "权力与政治",
    "power": "权力与政治",
    "politics": "权力与政治",
    "ai": "人工智能",
    "artificial intelligence": "人工智能",
    "creator": "创作者",
    "creators": "创作者",
    "philosophy": "哲学",
    "psychology": "心理学",
    "culture": "文化观察",
    "society": "社会观察",
}


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").split())


def _strip_title(text: str) -> str:
    return _clean_text(text).strip("。.!！?？；;：:")


def _sentences(text: str, limit: int = 2) -> list[str]:
    clean = _clean_text(text)
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
    return (parts or [clean])[:limit]


def _tag_label(tag: str) -> str:
    raw = _clean_text(tag).strip("#")
    mapped = TAG_ALIASES.get(raw.lower(), raw)
    return re.sub(r"\s+", "", mapped)


def _add_tag(tags: list[str], tag: str, limit: int = 12) -> None:
    label = _tag_label(tag)
    if not label:
        return
    normalized = label.lower()
    if any(item.lower() == normalized for item in tags):
        return
    if len(tags) < limit:
        tags.append(label)


def _semantic_tags(source: dict, insights: list[dict]) -> list[str]:
    text = " ".join(
        [
            str(source.get("title", "")),
            str(source.get("channel", "")),
            " ".join(source.get("tags", [])),
            " ".join(item.get("title", "") for item in insights[:6]),
            " ".join(item.get("body", "") for item in insights[:3]),
        ]
    ).lower()
    tags = []
    if any(word in text for word in ("ai", "gemini", "openai", "deepmind", "模型", "人工智能")):
        tags.extend(["人工智能", "AI商业化", "科技商业"])
    if any(word in text for word in ("token", "成本", "算力", "价格", "推理成本")):
        tags.extend(["Token经济学", "AI成本", "算力", "商业模式"])
    if any(
        word in text for word in ("grow an audience", "followers", "粉丝", "创作者", "内容创作", "audience")
    ):
        tags.extend(["创作者成长", "内容创作", "个人品牌"])
    if any(word in text for word in ("solitude", "alone", "孤独", "独处", "心理")):
        tags.extend(["心理学", "独处", "社会观察"])
    if any(word in text for word in ("职场", "效率", "管理", "工作流")):
        tags.extend(["职场思考", "效率系统"])
    if any(word in text for word in ("播客", "podcast", "访谈", "episode")):
        tags.append("播客笔记")
    return tags


def build_xhs_tags(source: dict, insights: list[dict], limit: int = 12) -> list[str]:
    tags = []
    content_limit = max(0, limit - 3)
    for tag in source.get("tags", []):
        _add_tag(tags, tag, limit=content_limit)
    for tag in _semantic_tags(source, insights):
        _add_tag(tags, tag, limit=content_limit)
    for tag in ("深度阅读", "Chora", "Rhizomata"):
        _add_tag(tags, tag, limit=limit)
    return tags


def _caption_hook(source: dict, insights: list[dict]) -> str:
    if insights:
        title = _strip_title(insights[0].get("title", ""))
        if title:
            return title
    return _strip_title(source.get("title", "Chora"))


def _caption_angle(source: dict, insights: list[dict]) -> tuple[str, str]:
    text = " ".join(
        [
            str(source.get("title", "")),
            str(source.get("channel", "")),
            " ".join(source.get("tags", [])),
            " ".join(item.get("title", "") for item in insights[:5]),
            " ".join(item.get("body", "") for item in insights[:3]),
        ]
    ).lower()
    if any(word in text for word in ("token", "算力", "模型", "ai", "人工智能", "成本")):
        return (
            "它更像一次成本结构的显影：谁能把智能调用得更便宜，谁就更接近下一轮分配权。",
            "适合关心 AI 商业化、模型成本和产品策略的人慢慢读。",
        )
    if any(word in text for word in ("创作者", "粉丝", "audience", "followers", "内容创作")):
        return (
            "它不是一篇涨粉技巧，而是在问创作者怎样从关系、信任和长期表达里长出来。",
            "适合正在做内容、产品叙事或个人品牌的人收藏。",
        )
    if any(word in text for word in ("孤独", "独处", "心理", "solitude", "alone")):
        return (
            "它把独处从情绪问题拆成一种生活结构：你如何理解自己，也会改变你如何进入关系。",
            "适合想把心理议题读得更细、更安静的人。",
        )
    if any(word in text for word in ("职场", "效率", "管理", "工作流")):
        return (
            "它讨论的不是多做一点，而是怎样重新安排注意力、边界和协作成本。",
            "适合正在调整工作流、团队节奏或个人效率系统的人。",
        )
    return (
        "它的价值不在于给一个标准答案，而是把问题背后的判断顺序重新排了一遍。",
        "适合需要快速抓住长文骨架，再回到原文深读的人。",
    )


def _caption_questions(insights: list[dict], limit: int = 3) -> list[str]:
    questions = []
    for insight in insights[:limit]:
        title = _strip_title(insight.get("title", ""))
        if not title:
            continue
        phrase = title.strip("。！？?!")
        if phrase.endswith(("吗", "么", "什么", "如何", "为何", "为什么")):
            questions.append(f"{phrase}？")
        else:
            questions.append(f"{phrase}意味着什么？")
    return questions


def build_xhs_caption(source: dict, insights: list[dict], brand: dict | None = None) -> str:
    brand = {**DEFAULT_BRAND, **(brand or {})}
    hook = _caption_hook(source, insights)
    angle, audience = _caption_angle(source, insights)
    questions = _caption_questions(insights)
    lines = [
        f"{hook}。",
        "",
        angle,
        "",
    ]
    if questions:
        lines.append("这组卡片主要拆三个问题：")
        for question in questions:
            lines.append(f"- {question}")
        lines.append("")
    for index, insight in enumerate(insights[:5], start=1):
        title = _strip_title(insight.get("title", ""))
        body = " ".join(_sentences(insight.get("body", ""), limit=1))
        if title and body:
            lines.append(f"{index}. {title}：{body}")
        elif title:
            lines.append(f"{index}. {title}")
    lines.extend(
        [
            "",
            audience,
            "",
            f"完整文章见 Chora：{brand['chora_url']}",
            f"也欢迎关注「{brand['rhizomata_name']}」，接收更多深度科技与人文笔记。",
        ]
    )
    return "\n".join(lines)


def build_xhs_publish_md(source: dict, insights: list[dict], brand: dict | None = None) -> str:
    brand = {**DEFAULT_BRAND, **(brand or {})}
    source_title = _strip_title(source.get("title", "Chora"))
    caption = build_xhs_caption(source, insights, brand=brand)
    tags = build_xhs_tags(source, insights)
    tags_text = " ".join(f"#{tag}" for tag in tags)
    first_comment = (
        f"完整文章已收录在 Chora：{brand['chora_url']}\n" f"公众号可搜「{brand['rhizomata_name']}」。"
    )
    insight_backup = []
    for index, insight in enumerate(insights, start=1):
        insight_title = _strip_title(insight.get("title", ""))
        body = _clean_text(insight.get("body", ""))
        if insight_title and body:
            insight_backup.append(f"{index}. {insight_title}：{body}")
        elif insight_title:
            insight_backup.append(f"{index}. {insight_title}")
    return "\n".join(
        [
            f"# {source_title}",
            "",
            "## 小红书正文｜复制此段",
            "```text",
            caption,
            "```",
            "",
            "## Tags｜复制此段",
            "```text",
            tags_text,
            "```",
            "",
            "## 首评｜可选",
            "```text",
            first_comment,
            "```",
            "",
            "## 发布清单",
            "- 图片顺序：按 `xhs/output/xhs-*.png` 文件名从小到大上传。",
            "- 图源记录：见 `xhs/assets/SOURCES.md`。",
            "- 若使用外部图源，发布前确认版权与是否署名。",
            "",
            "## 全部洞察备份｜不必整段复制",
            *insight_backup,
            "",
            f"来源：{source.get('channel', 'Unknown')}",
        ]
    )
