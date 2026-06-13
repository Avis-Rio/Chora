from __future__ import annotations

import re

from distribution_pipeline.renderers.guizang.category_router import detect_rednote_category
from distribution_pipeline.renderers.guizang.content_allocator import assign_copy_slots
from distribution_pipeline.renderers.xhs_plan import build_xhs_card_plan


METRIC_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>%|％|倍|年|个月|月|周|天|小时|分钟|秒|美元|美金|元|万|亿|k|K|m|M|b|B)?"
)


EDITORIAL_RECIPES = {
    "cover": ["M01", "M16"],
    "insight": ["M02", "M03", "M05", "M06", "M08", "M09", "M10", "M11", "M14", "M15"],
    "concept-map": ["M14"],
    "philosophy": ["M13"],
    "closing": ["M07"],
}

SWISS_RECIPES = {
    "cover": ["S01", "S08"],
    "insight": ["S02", "S03", "S04", "S05", "S06", "S07", "S09", "S10", "S11", "S12"],
    "concept-map": ["S06", "S09", "S12"],
    "philosophy": ["S12"],
    "closing": ["S07", "S12"],
}


def _recipe_table(mode: str) -> dict[str, list[str]]:
    if mode == "editorial":
        return EDITORIAL_RECIPES
    if mode == "swiss":
        return SWISS_RECIPES
    raise ValueError(f"Unknown guizang mode: {mode}")


def _role(card_type: str) -> str:
    return {
        "cover-poster": "cover",
        "single-insight": "insight",
        "concept-map": "concept-map",
        "philosophical-card": "philosophy",
        "closing-card": "closing",
    }.get(card_type, "insight")


def _choose_recipe(candidates: list[str], previous: str | None, offset: int = 0) -> str:
    if not candidates:
        raise ValueError("Guizang recipe candidates cannot be empty")
    ordered = candidates[offset % len(candidates) :] + candidates[: offset % len(candidates)]
    for recipe in ordered:
        if recipe != previous:
            return recipe
    return ordered[0]


def _sparse_recipe(previous: str | None) -> str:
    return "M11" if previous != "M11" else "M09"


def content_profile(source: dict, insights: list[dict]) -> str:
    text = " ".join(
        [
            str(source.get("title", "")),
            str(source.get("channel", "")),
            " ".join(source.get("tags", [])),
            " ".join(item.get("title", "") for item in insights[:5]),
            " ".join(item.get("body", "") for item in insights[:3]),
        ]
    ).lower()
    if any(word in text for word in ("grow an audience", "followers", "粉丝", "受众", "创作者", "社交媒体", "networking")):
        return "creator-growth"
    if any(word in text for word in ("people disappear", "being alone", "solitude", "孤独", "孤寂", "独处", "回避", "第三空间", "蛰居")):
        return "solitude-psychology"
    if any(word in text for word in ("gemini", "deepmind", "openai", "ai", "模型", "算力", "视觉")):
        return "ai-tech"
    return "default"


def _split_points(text: str, limit: int = 5) -> list[str]:
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


def _strong_sentence_count(text: str) -> int:
    clean = str(text or "").strip()
    if not clean:
        return 0
    count = sum(1 for char in clean if char in "。！？；;")
    return max(count, 1)


def _has_checklist_signal(text: str) -> bool:
    return any(word in text for word in ("步骤", "方法", "清单", "指南", "行动", "建议", "习惯", "原则", "要点", "做法"))


def _has_comparison_signal(text: str) -> bool:
    return (
        ("不是" in text and "而是" in text)
        or ("before" in text.lower() and "after" in text.lower())
        or any(word in text for word in ("旧方式", "新方式", "前后", "对比", "误区", "真相"))
    )


def _extract_metric_tokens(text: str, limit: int = 4) -> list[dict]:
    tokens = []
    seen = set()
    for match in METRIC_RE.finditer(str(text or "")):
        raw = match.group(0).strip()
        if not raw or raw in seen:
            continue
        seen.add(raw)
        value = float(match.group("num"))
        unit = match.group("unit") or ""
        if unit in ("k", "K"):
            value *= 1_000
        elif unit in ("m", "M"):
            value *= 1_000_000
        elif unit in ("b", "B"):
            value *= 1_000_000_000
        tokens.append(
            {
                "raw": raw,
                "value": value,
                "unit": unit,
                "source": "extracted",
            }
        )
        if len(tokens) >= limit:
            break
    return tokens


def _build_metric_stats(text: str, display_index: str, chips: list[dict]) -> list[dict]:
    tokens = _extract_metric_tokens(text, limit=3)
    if tokens:
        heights = [260, 220, 180]
        return [
            {
                "num": token["raw"],
                "lbl": "EXTRACTED",
                "height": heights[index],
                "source": "extracted",
            }
            for index, token in enumerate(tokens[:3])
        ]
    return []


def _sequence_recipe(
    category: dict,
    mode: str,
    role: str,
    offset: int,
    previous: str | None,
    has_image: bool,
    has_subject_map: bool,
) -> str | None:
    sequence = (category.get("deck_sequence") or {}).get(mode) or ()
    if role != "insight" or not sequence:
        return None

    insight_sequence = [recipe for recipe in sequence if recipe[0] in ("M", "S") and recipe not in ("M01", "S01", "M07", "S07")]
    if not insight_sequence:
        return None

    ordered = insight_sequence[offset % len(insight_sequence) :] + insight_sequence[: offset % len(insight_sequence)]
    for recipe in ordered:
        if recipe == previous:
            continue
        if recipe in ("M02", "M06", "M10") and not has_image:
            continue
        if recipe in ("M16", "S08") and not (has_image and has_subject_map):
            continue
        return recipe
    return None


def _chip_items(title: str, body: str, profile: str = "default", limit: int = 3) -> list[dict]:
    text = f"{title} {body}"
    profile_rules = {
        "creator-growth": [
            (("算法", "黑箱", "平台"), "算法"),
            (("社交", "关系", "互惠", "networking"), "社交"),
            (("创作", "原创", "内容", "表达"), "创作"),
            (("系统", "流程", "杠杆", "复利"), "系统"),
            (("初学者", "优势", "专注"), "优势"),
        ],
        "ai-tech": [
            (("数据", "合成", "筛选", "清洗"), "数据"),
            (("模型", "GPT", "Gemini", "Transformer"), "模型"),
            (("组织", "团队", "合并", "co-lead"), "组织"),
            (("时间", "时机", "窗口", "周期"), "时间"),
            (("成本", "算力", "Token", "GPU"), "成本"),
            (("视觉", "图像", "理解"), "视觉"),
        ],
        "solitude-psychology": [
            (("孤独", "孤寂", "独处"), "孤独"),
            (("回避", "焦虑", "杏仁核"), "心理"),
            (("第三空间", "公共空间", "咖啡馆", "图书馆"), "空间"),
            (("数字", "网络", "线上", "社群"), "数字"),
            (("身份", "表演", "不发布", "点赞"), "身份"),
            (("沉默", "自主权", "算法"), "自主"),
        ],
    }
    rules = profile_rules.get(profile, []) + [
        (("数据", "合成", "筛选", "清洗"), "数据"),
        (("模型", "GPT", "Gemini", "Transformer"), "模型"),
        (("组织", "团队", "合并", "co-lead"), "组织"),
        (("时间", "时机", "窗口", "周期"), "时间"),
        (("成本", "算力", "Token", "GPU"), "成本"),
        (("视觉", "图像", "理解"), "视觉"),
        (("流动", "人才", "知识"), "流动"),
        (("风险", "代价", "偏差"), "风险"),
    ]
    labels = []
    for needles, label in rules:
        if label not in labels and any(needle in text for needle in needles):
            labels.append(label)
        if len(labels) >= limit:
            break
    return [
        {
            "index": f"{index:02d}",
            "title": label,
            "note": "",
            "generated": True,
        }
        for index, label in enumerate(labels[:limit], start=1)
    ]


def _growth_title(title: str) -> str:
    clean = str(title or "").strip()
    if not clean:
        return clean
    match = re.search(r"最大风险不是(.+?)，而是(.+?)[。.!！?？]?$", clean)
    if match:
        rejected = match.group(1).strip()
        actual = match.group(2).strip()
        if rejected and actual:
            return f"{actual}，比{rejected}更危险。"
    if len(clean) <= 26:
        return clean
    for before, after in (
        ("的本质是", "其实是"),
        ("正在制造一个", "制造了"),
        ("是大模型竞争中", "是 AI 竞争中"),
    ):
        clean = clean.replace(before, after)
    return clean


def _choose_insight_recipe(card: dict, has_image: bool, previous: str | None, offset: int, profile: str = "default") -> str:
    if has_image:
        return "M10"

    body = card.get("body", "")
    points = _split_points(body, limit=5)
    title = card.get("title", "")
    text = f"{title} {body}"

    if _has_comparison_signal(title) and previous != "M15":
        return "M15"
    if _has_checklist_signal(text) and len(points) >= 3 and previous != "M05":
        return "M05"

    if profile == "creator-growth":
        if "算法" in text and len(title) <= 24:
            return "M09" if previous != "M09" else "M11"
        if "系统" in text or "流程" in text or "杠杆" in text:
            return _sparse_recipe(previous) if len(body) <= 180 else ("M14" if previous != "M14" else "M11")
        if len(points) >= 4:
            return "M08" if previous != "M08" else "M11"

    if profile == "solitude-psychology":
        if len(points) <= 2 and len(body) <= 180:
            return "M11" if previous != "M11" else "M09"
        if len(points) >= 3:
            return "M08" if previous != "M08" else "M11"

    if _strong_sentence_count(body) <= 1:
        if len(body) <= 42 and len(title) <= 24:
            return "M09" if previous != "M09" else "M11"
        if len(body) <= 140:
            return _sparse_recipe(previous)
    if len(points) <= 2 and len(body) <= 150:
        return _sparse_recipe(previous)
    if len(points) >= 4:
        return "M08" if previous != "M08" else "M11"
    if len(points) >= 3 and any(word in text for word in ("驱使", "导致", "反而", "因为", "所以", "窗口", "路径", "路线")):
        return "M14" if previous != "M14" else "M03"
    return _choose_recipe(["M03", "M11", "M09"], previous, offset=offset)


def _choose_editorial_category_recipe(card: dict, has_image: bool, previous: str | None, category: dict) -> str | None:
    key = category.get("key")
    body = card.get("body", "")
    points = _split_points(body, limit=5)
    if key == "travel" and has_image:
        return "M02" if previous != "M02" else "M10"
    if key == "emotion":
        if len(points) <= 2 or len(body) <= 180:
            return "M09" if previous != "M09" else "M11"
        return "M11" if previous != "M11" else "M04"
    if key in ("food", "makeup", "fitness") and _has_checklist_signal(f"{card.get('title', '')} {body}"):
        return "M14" if previous != "M14" else "M05"
    if key == "film" and has_image:
        return "M10"
    return None


def _choose_swiss_insight_recipe(
    card: dict,
    has_image: bool,
    has_subject_map: bool,
    previous: str | None,
    offset: int,
    category: dict | None = None,
) -> str:
    body = card.get("body", "")
    title = card.get("title", "")
    text = f"{title} {body}"
    lowered = text.lower()
    points = _split_points(body, limit=6)

    if has_image and has_subject_map and previous != "S08":
        return "S08"
    if any(word in lowered for word in ("top", "ranking", "rank")) or any(word in text for word in ("排名", "前十", "最高", "最低")):
        return "S10" if previous != "S10" else "S03"
    if (
        _has_comparison_signal(text)
        or "不等于" in text
        or ("强模型" in text and "弱模型" in text)
    ) and previous != "S02":
        return "S02"
    if any(word in text for word in ("风险", "陷阱", "错误", "误区", "不要", "不能", "警惕")) and previous != "S05":
        return "S05"
    if any(word in text for word in ("流程", "路径", "系统", "架构", "步骤", "链路", "工作流")) and previous != "S06":
        return "S06"
    if _has_checklist_signal(text) and len(points) >= 3 and previous != "S11":
        return "S11"
    if (
        _extract_metric_tokens(text, limit=1)
        and any(word in text for word in ("数据", "指标", "增长", "成本", "Token", "百分比", "%", "倍"))
        and previous != "S09"
    ):
        return "S09"
    sequence = _sequence_recipe(category or {}, "swiss", "insight", offset, previous, has_image, has_subject_map)
    if sequence:
        return sequence
    if len(points) >= 3 and previous != "S12":
        return "S12"
    return _choose_recipe(["S03", "S04", "S07"], previous, offset=offset)


def _compress_cover_clause(clause: str) -> str:
    compressed = str(clause or "").strip()
    replacements = {
        "翻身之战": "翻身战",
        "视觉理解模型": "视觉理解",
        "前核心科学家": "科学家",
    }
    for before, after in replacements.items():
        compressed = compressed.replace(before, after)
    return compressed


def _short_cover_lines(title: str) -> list[str]:
    clean = str(title or "").strip()
    if not clean:
        return ["Chora"]
    clean = clean.split("：专访", 1)[0].split(":专访", 1)[0]
    clauses = []
    current = ""
    for char in clean:
        if char in "、，,：:｜|":
            if current.strip():
                clauses.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        clauses.append(current.strip())
    clauses = [_compress_cover_clause(clause) for clause in clauses]
    useful = [clause for clause in clauses if len(clause) <= 12]
    if len(useful) >= 2:
        return useful[:2]
    if clauses:
        first = clauses[0]
        return [first[:14], first[14:28]] if len(first) > 14 else [first]
    return [clean[:14], clean[14:28]] if len(clean) > 14 else [clean]


def _closing_items(insights: list[dict]) -> list[dict]:
    items = []
    for index, insight in enumerate(insights[:4], start=1):
        body_points = _split_points(insight.get("body", ""), limit=1)
        items.append(
            {
                "index": f"{index:02d}",
                "title": insight.get("title", ""),
                "note": body_points[0] if body_points else insight.get("summary", ""),
            }
        )
    return items


def _asset_matches_page(asset: dict, page_id: str, insight_index: int | None = None) -> bool:
    target_insight_index = asset.get("target_insight_index")
    if target_insight_index is not None:
        return insight_index is not None and str(target_insight_index) == str(insight_index)
    return page_id in asset.get("target_pages", [])


def _asset_for_page(image_assets: dict, page_id: str, insight_index: int | None = None) -> dict | None:
    for asset_group in ("local_assets", "selected_assets"):
        for asset in image_assets.get(asset_group, []):
            if asset.get("status") not in (None, "available"):
                continue
            if not _asset_matches_page(asset, page_id, insight_index):
                continue
            if not asset.get("render_path"):
                continue
            return {
                "asset_id": asset.get("asset_id", ""),
                "src": asset.get("render_path", ""),
                "caption": asset.get("caption", ""),
                "role": asset.get("role", ""),
                "object_position": asset.get("object_position", "center 50%"),
                "subject_map": asset.get("subject_map"),
                "provider": asset.get("provider", ""),
                "source_url": asset.get("source_url", ""),
                "author": asset.get("author", ""),
                "target_insight_index": asset.get("target_insight_index"),
            }
    return None


def _request_for_page(image_assets: dict, page_id: str) -> dict | None:
    for request in image_assets.get("requests", []):
        if page_id in request.get("target_pages", []):
            return request
    return None


def _page_from_card(
    card: dict,
    source: dict,
    insights: list[dict],
    image_assets: dict,
    recipe: str,
    index: int,
    role: str,
    profile: str,
    category: dict,
    mode: str,
    brand: dict,
) -> dict:
    original_title = card.get("title", "")
    title = _growth_title(original_title) if card.get("strategy") == "growth-depth" and role == "insight" else original_title
    body = card.get("body", "")
    page_id = f"xhs-{index:02d}"
    insight_number = card.get("insight_index") or max(index - 1, 1)
    image = _asset_for_page(image_assets, page_id, card.get("insight_index"))
    chips = _chip_items(title, body, profile)
    display_index = f"{int(insight_number):02d}" if role == "insight" else f"{index:02d}"
    metric_source_text = f"{title} {body} {card.get('reader_takeaway', '')}"
    metric_tokens = _extract_metric_tokens(metric_source_text, limit=4)
    page = {
        "id": page_id,
        "platform": "xhs",
        "role": role,
        "recipe": recipe,
        "title": title,
        "original_title": original_title,
        "body": body,
        "kicker": {
            "cover": "Issue 01",
            "insight": f"Insight {int(insight_number):02d}",
            "concept-map": "Structure",
            "philosophy": "Philosophical Epilogue",
            "closing": "Closing Note",
        }[role],
        "footer": f"{source.get('channel', 'Chora')} · Rhizomata",
        "insight_index": card.get("insight_index"),
        "display_index": display_index,
        "points": _split_points(body, limit=4),
        "items": [],
        "source_title": source.get("title", ""),
        "image": image,
        "image_request": _request_for_page(image_assets, page_id),
        "reader_takeaway": card.get("reader_takeaway", ""),
        "chips": chips,
        "strategy": card.get("strategy", "archive"),
        "content_profile": profile,
        "rednote_category": category,
        "scope_notes": category.get("scope_notes", ()),
        "metric_tokens": metric_tokens,
        "stats": _build_metric_stats(metric_source_text, display_index, chips) if mode == "swiss" else [],
        "qa_flags": [],
    }
    if role == "cover":
        page["title_lines"] = card.get("title_lines") or _short_cover_lines(source.get("title", title))
        page["title"] = "\n".join(page["title_lines"])
    if role == "closing":
        page["items"] = card.get("items") or _closing_items(insights)
        page["cta"] = {
            "label": "阅读全文",
            "site_label": "Chora",
            "url": brand.get("chora_url", "https://chora.avisionary.top"),
            "qr_label": f"公众号 · {brand.get('rhizomata_name', 'Rhizomata')}",
            "qr_src": brand.get("rhizomata_qr", ""),
        }
    if role == "concept-map":
        page["items"] = _closing_items(insights[:3])
    if role == "philosophy":
        page["style"] = card.get("style", "")
    if role == "insight" and not page["points"]:
        page["points"] = [body] if body else []
    if recipe in ("M16", "S08"):
        page["qa_flags"].append("text_on_image_requires_subject_map")
        page["qa_flags"].append("thumbnail_check_required")
        if not (image and image.get("subject_map")):
            page["qa_flags"].append("unsafe_overlay_recipe")
    if metric_tokens:
        page["qa_flags"].append("uses_extracted_metrics")
    elif mode == "swiss" and recipe in ("S09", "S10", "S12"):
        page["qa_flags"].append("uses_proxy_metrics")
    return assign_copy_slots(page)


def build_xhs_pages(package: dict, max_cards: int | None = None, mode: str = "editorial") -> list[dict]:
    recipes = _recipe_table(mode)
    source = package["source"]
    insights = package["insights"]
    profile = content_profile(source, insights)
    category = detect_rednote_category(source, insights)
    image_assets = package.get("image_assets", {})
    brand = package.get("brand", {})
    cards = build_xhs_card_plan(
        source,
        insights,
        max_cards=max_cards,
        epilogue=package.get("philosophical_epilogue"),
        strategy="growth-depth" if mode == "editorial" else "archive",
    )

    pages = []
    previous_recipe = None
    insight_offset = 0
    for index, card in enumerate(cards, start=1):
        role = _role(card.get("type", ""))
        page_id = f"xhs-{index:02d}"
        offset = insight_offset if role == "insight" else 0
        image_asset = _asset_for_page(image_assets, page_id, card.get("insight_index"))
        has_image = bool(image_asset)
        has_subject_map = bool((image_asset or {}).get("subject_map"))
        if mode == "editorial" and role == "cover" and has_image and has_subject_map:
            recipe = "M16" if previous_recipe != "M16" else "M01"
        elif mode == "editorial" and role == "insight":
            recipe = (
                _choose_editorial_category_recipe(card, has_image, previous_recipe, category)
                or _sequence_recipe(category, mode, role, offset, previous_recipe, has_image, has_subject_map)
                or _choose_insight_recipe(card, has_image, previous_recipe, offset, profile)
            )
        elif mode == "swiss" and role == "insight":
            recipe = _choose_swiss_insight_recipe(card, has_image, has_subject_map, previous_recipe, offset, category)
        else:
            recipe = _choose_recipe(recipes[role], previous_recipe, offset=offset)
        pages.append(_page_from_card(card, source, insights, image_assets, recipe, index, role, profile, category, mode, brand))
        previous_recipe = recipe
        if role == "insight":
            insight_offset += 1
    return pages[:max_cards] if max_cards is not None else pages
