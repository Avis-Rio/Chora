from __future__ import annotations

import re
from pathlib import Path

from distribution_pipeline.renderers.guizang.category_router import detect_rednote_category
from distribution_pipeline.renderers.guizang.content_allocator import assign_copy_slots
from distribution_pipeline.renderers.guizang.screenshot_treatment import detect_screenshot
from distribution_pipeline.renderers.guizang.subject_mapper import build_subject_map
from distribution_pipeline.renderers.guizang.title_breaker import semantic_title_lines
from distribution_pipeline.renderers.guizang.title_budget import title_variants
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
    "insight": ["S02", "S03", "S04", "S05", "S06", "S07", "S09", "S10", "S11", "S12", "S13"],
    "concept-map": ["S06", "S09", "S12", "S13"],
    "philosophy": ["S12", "S07"],
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


def _content_payload(card: dict) -> dict:
    body = str(card.get("body") or "")
    source_body = str(card.get("source_body") or "")
    points = card.get("points") or _split_points(body, limit=5)
    details = card.get("details") or _split_points(source_body or body, limit=5)
    pullquote = str(card.get("pullquote") or "")
    chars = len("".join(ch for ch in " ".join([body, source_body, pullquote, *points, *details]) if ch.strip()))
    return {
        "chars": chars,
        "points": len(points),
        "details": len(details),
        "has_pullquote": bool(pullquote),
        "low": chars < 160 or len(points) < 2,
    }


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


def _has_map_signal(text: str) -> bool:
    return any(word in text for word in (
        "地理", "地域", "地缘", "跨境", "出海", "迁移", "流动", "流向", "路线", "供应链",
        "东西方", "东方", "西方", "东移", "西移", "全球化", "区域", "国家", "中美", "中欧",
        "欧美", "航线", "物流", "贸易", "走廊", "通道", "节点", "枢纽",
    ))


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


def _extract_map_nodes(title: str, body: str, limit: int = 4) -> list[dict]:
    text = f"{title} {body}"
    candidates = [
        "中国", "美国", "欧洲", "东南亚", "中东", "非洲", "拉美", "印度", "日本", "韩国",
        "硅谷", "华尔街", "深圳", "北京", "上海", "香港", "新加坡", "迪拜",
        "东方", "西方", "全球南方", "发达国家", "新兴市场",
    ]
    # 按文本出现顺序收集，避免标题里的“东方”插队到 body“中东”之前
    nodes = []
    seen = set()
    for phrase in candidates:
        pos = text.find(phrase)
        if pos == -1:
            continue
        nodes.append((pos, phrase))
    nodes.sort(key=lambda x: x[0])
    result = []
    for _, phrase in nodes:
        if phrase not in seen:
            seen.add(phrase)
            result.append({"label": phrase, "role": "region"})
        if len(result) >= limit:
            break
    if len(result) < 2:
        return []
    return result


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


def _has_swiss_kpi_signal(text: str) -> bool:
    return (
        len(_extract_metric_tokens(text, limit=4)) >= 2
        and any(word in text for word in ("数据", "指标", "增长", "成本", "Token", "百分比", "%", "倍"))
    )


def _enumerated_terms(text: str, limit: int = 5) -> list[str]:
    clean = " ".join(str(text or "").split())
    if "、" not in clean:
        return []
    for clause in re.split(r"[。！？；;]", clean):
        if "、" not in clause:
            continue
        head = re.split(r"[，,：:]", clause, maxsplit=1)[0]
        parts = [part.strip() for part in head.split("、") if part.strip()]
        if len(parts) < 3:
            continue
        parts[-1] = re.sub(r"(构成|形成|决定|支撑|组成).*$", "", parts[-1]).strip() or parts[-1]
        if all(1 <= len(part) <= 16 for part in parts[:limit]):
            return parts[:limit]
    return []


def _pipeline_note_for_term(term: str) -> str:
    lowered = str(term or "").lower()
    if any(word in term for word in ("电价", "价格", "成本", "算力")):
        return "成本底座"
    if "moe" in lowered or any(word in term for word in ("模型", "架构", "路由")):
        return "效率结构"
    if any(word in term for word in ("云", "厂商", "整合", "供应", "链路")):
        return "供给链路"
    if any(word in term for word in ("输入", "数据", "素材")):
        return "输入层"
    if any(word in term for word in ("处理", "筛选", "清洗")):
        return "处理层"
    if any(word in term for word in ("发布", "输出", "交付")):
        return "输出层"
    if any(word in term for word in ("复盘", "反馈", "迭代")):
        return "迭代层"
    return "结构节点"


def _pipeline_items_from_text(title: str, body: str, limit: int = 3) -> list[dict]:
    terms = _enumerated_terms(body, limit=limit) or _enumerated_terms(title, limit=limit)
    return [
        {
            "index": f"{index:02d}",
            "title": term,
            "note": _pipeline_note_for_term(term),
        }
        for index, term in enumerate(terms[:limit], start=1)
    ]


def _pipeline_item_count(title: str, body: str) -> int:
    return max(len(_split_points(body, limit=6)), len(_enumerated_terms(body)), len(_enumerated_terms(title)))


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
    card_text: str = "",
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
        if mode == "swiss" and recipe == "S09" and not _has_swiss_kpi_signal(card_text):
            continue
        if mode == "swiss" and recipe == "S06" and _pipeline_item_count(card_text, card_text) < 3:
            continue
        # 短内容避免 S12 矩阵密度不足，改用 fallback 密集 recipe
        if mode == "swiss" and recipe == "S12" and len(str(card_text or "").strip()) < 160:
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
    body = card.get("body", "")
    payload = _content_payload(card)
    points = card.get("points") or _split_points(body, limit=5)
    title = card.get("title", "")
    text = f"{title} {body} {card.get('source_body', '')}"

    if _has_comparison_signal(title) and previous != "M15":
        return "M15"

    if payload["low"]:
        # 低密度内容：候选大气/留白模板（M09 atmospheric）承载稀疏文案，避免密集模板空荡。
        if payload["details"] >= 3 or len(points) >= 3:
            return "M08" if previous != "M08" else "M14"
        return "M09" if previous != "M09" else "M11"

    if has_image and payload["details"] >= 2:
        return "M10"

    if _has_checklist_signal(text) and len(points) >= 3 and previous != "M05":
        return "M05"

    if profile == "creator-growth":
        if "算法" in text and len(title) <= 24:
            return _sparse_recipe(previous)
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
            return _sparse_recipe(previous)
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
            return _sparse_recipe(previous)
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

    if _has_map_signal(text) and previous != "S13":
        map_nodes = _extract_map_nodes(title, body)
        if len(map_nodes) >= 2:
            return "S13"
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
    if (
        any(word in text for word in ("流程", "路径", "系统", "架构", "步骤", "链路", "工作流"))
        and _pipeline_item_count(title, body) >= 3
        and previous != "S06"
    ):
        return "S06"
    if _has_checklist_signal(text) and len(points) >= 3 and previous != "S11":
        return "S11"
    if _has_swiss_kpi_signal(text) and previous != "S09":
        return "S09"
    if (
        _extract_metric_tokens(text, limit=1)
        and any(word in text for word in ("数据", "指标", "增长", "成本", "Token", "百分比", "%", "倍"))
        and previous != "S03"
    ):
        return "S03"
    sequence = _sequence_recipe(category or {}, "swiss", "insight", offset, previous, has_image, has_subject_map, text)
    if sequence:
        return sequence
    if len(points) >= 3 and previous != "S12":
        body_text = str(body or "").strip()
        # 短内容避免 S12/S11 矩阵/ledger 密度不足，改用 S03 file card 靠结构填满页面
        if len(body_text) < 160 and not _has_checklist_signal(text):
            return "S03" if previous != "S03" else "S07"
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
    # Prefer natural punctuation clauses (≤18 chars) — they read more like
    # editorial pull-quotes and stay within two visual lines at 62px / 1080px.
    useful = [clause for clause in clauses if len(clause) <= 18]
    if len(useful) >= 2:
        return useful[:2]
    if useful:
        return useful[:1]
    if clauses:
        first = clauses[0]
        return semantic_title_lines(first, target=12, max_lines=2, min_tail=3)
    return semantic_title_lines(clean, target=12, max_lines=2, min_tail=3)




def _cap_title_chars(text: str, limit: int) -> str:
    """硬 cap 標題中文字符數（標點計入），超限加省略號。"""
    clean = str(text or "").strip()
    if not clean or len(clean) <= limit:
        return clean
    return clean[:limit].rstrip("，,。.!！?？；;：:、 ") + "…"


def _cover_line_limit(line_count: int) -> int:
    """Per-line char cap that loosens as we allow more lines, so longer titles
    keep more of their tail instead of being aggressively truncated."""
    return {1: 20, 2: 18, 3: 14}.get(line_count, 12)

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


def _resolve_local_image_path(render_path: str, image_assets: dict) -> Path | None:
    if not render_path or render_path.startswith(("http://", "https://", "data:")):
        return None
    candidate = Path(render_path)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    render_root = image_assets.get("_render_root")
    if render_root:
        candidate = Path(render_root) / render_path
        return candidate if candidate.exists() else None
    return None


def _asset_for_page(image_assets: dict, page_id: str, insight_index: int | None = None) -> dict | None:
    for asset_group in ("local_assets", "selected_assets"):
        for asset in image_assets.get(asset_group, []):
            if asset.get("status") not in (None, "available"):
                continue
            if not _asset_matches_page(asset, page_id, insight_index):
                continue
            if not asset.get("render_path"):
                continue
            image_meta = {
                "asset_id": asset.get("asset_id", ""),
                "src": asset.get("render_path", ""),
                "caption": asset.get("caption", ""),
                "alt": asset.get("alt", ""),
                "filename": asset.get("filename", ""),
                "role": asset.get("role", ""),
                "object_position": asset.get("object_position", "center 50%"),
                "subject_map": asset.get("subject_map"),
                "provider": asset.get("provider", ""),
                "source_url": asset.get("source_url", ""),
                "author": asset.get("author", ""),
                "target_insight_index": asset.get("target_insight_index"),
            }
            image_meta["screenshot"] = detect_screenshot(image_meta, {"role": asset.get("role", "")})
            # 丁项 + vision 增强：若上游 asset 没附 subject_map，按 caption/alt 启发式生成；
            # 若图有本地文件，传 image_path 触发 vision 增强（cache → vision → 启发式 fallback）
            if not image_meta.get("subject_map"):
                render_path = image_meta.get("src", "")
                image_path = _resolve_local_image_path(render_path, image_assets)
                image_meta["subject_map"] = build_subject_map(
                    image_meta,
                    {"role": asset.get("role", "")},
                    image_path=image_path,
                    cache_dir=image_path.parent if image_path else None,
                )
            return image_meta
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
    title = original_title if card.get("title_lines") else (_growth_title(original_title) if card.get("strategy") == "growth-depth" and role == "insight" else original_title)
    body = card.get("body", "")
    page_id = f"xhs-{index:02d}"
    insight_number = card.get("insight_index") or max(index - 1, 1)
    image = _asset_for_page(image_assets, page_id, card.get("insight_index"))
    chips = _chip_items(title, body, profile)
    display_index = f"{int(insight_number):02d}" if role == "insight" else f"{index:02d}"
    pullquote = str(card.get("pullquote") or "").strip()
    subhead = str(card.get("subhead") or "").strip()
    metric_source_text = f"{title} {body} {pullquote}"
    metric_tokens = _extract_metric_tokens(metric_source_text, limit=4)
    title_variant = title_variants(title, recipe)
    card_title_lines = [str(line).strip() for line in (card.get("title_lines") or []) if str(line).strip()]
    page = {
        "id": page_id,
        "platform": "xhs",
        "role": role,
        "recipe": recipe,
        "title": title,
        "display_title": title,
        "short_title": title_variant["short_title"],
        "title_lines": card_title_lines or semantic_title_lines(title, target=title_variant["title_budget"]["line_chars"], max_lines=8, min_tail=3),
        "title_budget": {**title_variant["title_budget"], "max_lines": 8},
        "original_title": original_title,
        "subhead": subhead,
        "body": body,
        "source_body": card.get("source_body", body),
        "details": card.get("details") or [],
        "copy_density": card.get("copy_density", ""),
        "min_payload_ok": card.get("min_payload_ok", False),
        "payload_chars": card.get("payload_chars", 0),
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
        "points": card.get("points") or _split_points(body, limit=5),
        "items": card.get("details") or [],
        "source_title": source.get("title", ""),
        "image": image,
        "image_request": _request_for_page(image_assets, page_id),
        "pullquote": pullquote,
        "reader_takeaway": pullquote or card.get("reader_takeaway", ""),
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
        # Cover 標題：先 _short_cover_lines 切分，再按行數放宽每行字數上限
        raw_lines = card.get("title_lines") or _short_cover_lines(source.get("title", title))
        line_cap = _cover_line_limit(min(len(raw_lines), 3))
        page["title_lines"] = [_cap_title_chars(line, line_cap) for line in raw_lines][:3]
        page["title"] = "\n".join(page["title_lines"])
        page["display_title"] = page["title"]
        page["short_title"] = "".join(page["title_lines"][:1])[:10]
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
    if mode == "swiss" and recipe == "S06":
        pipeline_items = _pipeline_items_from_text(title, body, limit=3)
        if pipeline_items:
            page["items"] = pipeline_items
    if mode == "swiss" and recipe == "S13":
        map_nodes = _extract_map_nodes(title, body)
        if map_nodes:
            page["map_nodes"] = map_nodes
            page["map_route"] = {
                "origin": map_nodes[0]["label"],
                "destination": map_nodes[-1]["label"],
                "stops": [n["label"] for n in map_nodes[1:-1]],
            }
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
        card_copies=package.get("card_copy"),
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
        # 丁项：自动生成的 subject_map（image metadata 空）不算有效，需真实 vision
        sm = (image_asset or {}).get("subject_map") or {}
        has_subject_map = bool(sm) and not sm.get("auto_generated", False)
        if mode == "editorial" and role == "cover" and has_image and has_subject_map:
            recipe = "M16" if previous_recipe != "M16" else "M01"
        elif mode == "editorial" and role == "insight":
            hinted_recipe = card.get("recipe_hint") if card.get("recipe_hint") != previous_recipe else ""
            if hinted_recipe in ("M02", "M06", "M10") and not has_image:
                hinted_recipe = ""
            recipe = (
                _choose_editorial_category_recipe(card, has_image, previous_recipe, category)
                or ("M10" if has_image and previous_recipe != "M10" else "")
                or _sequence_recipe(category, mode, role, offset, previous_recipe, has_image, has_subject_map)
                or hinted_recipe
                or _choose_insight_recipe(card, has_image, previous_recipe, offset, profile)
            )
        elif mode == "swiss" and role == "insight":
            recipe = _choose_swiss_insight_recipe(card, has_image, has_subject_map, previous_recipe, offset, category)
        elif mode == "swiss" and role == "philosophy":
            # philosophy 默认用更密集的 S07，避免 S12 矩阵在哲思页密度不足
            recipe = "S07" if previous_recipe != "S07" else "S12"
        elif mode == "swiss" and role == "closing":
            recipe = "S07"
        else:
            recipe = _choose_recipe(recipes[role], previous_recipe, offset=offset)
        pages.append(_page_from_card(card, source, insights, image_assets, recipe, index, role, profile, category, mode, brand))
        previous_recipe = recipe
        if role == "insight":
            insight_offset += 1
    return pages[:max_cards] if max_cards is not None else pages
