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
    "business": "商业思考",
    "power & politics": "权力与政治",
    "power": "权力与政治",
    "politics": "权力与政治",
    "ai": "人工智能",
    "artificial intelligence": "人工智能",
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
        tags.extend(["人工智能", "AI", "科技"])
    if any(word in text for word in ("token", "成本", "算力", "价格")):
        tags.extend(["Token经济学", "AI成本"])
    if any(word in text for word in ("grow an audience", "followers", "粉丝", "创作者", "内容创作")):
        tags.extend(["创作者成长", "内容创作"])
    if any(word in text for word in ("solitude", "alone", "孤独", "独处", "心理")):
        tags.extend(["心理学", "社会观察"])
    if any(word in text for word in ("职场", "效率", "管理", "工作流")):
        tags.extend(["职场思考", "效率系统"])
    return tags


def build_xhs_tags(source: dict, insights: list[dict], limit: int = 12) -> list[str]:
    tags = []
    for tag in source.get("tags", []):
        _add_tag(tags, tag, limit=limit)
    for tag in _semantic_tags(source, insights):
        _add_tag(tags, tag, limit=limit)
    for tag in ("深度阅读", "Chora", "Rhizomata"):
        _add_tag(tags, tag, limit=limit)
    return tags


def _caption_hook(source: dict, insights: list[dict]) -> str:
    if insights:
        title = _strip_title(insights[0].get("title", ""))
        if title:
            return title
    return _strip_title(source.get("title", "Chora"))


def build_xhs_caption(source: dict, insights: list[dict], brand: dict | None = None) -> str:
    brand = {**DEFAULT_BRAND, **(brand or {})}
    hook = _caption_hook(source, insights)
    lines = [
        f"{hook}。",
        "",
        "这组卡片整理自 Chora 的深度改写文章。它不只是在复述观点，而是把原文里的判断框架拆成几层：",
        "",
    ]
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
            "如果只记一件事：真正有价值的不是单个结论，而是它如何改变我们理解技术、组织与社会的方式。",
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
        f"完整文章已收录在 Chora：{brand['chora_url']}\n"
        f"公众号可搜「{brand['rhizomata_name']}」。"
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
