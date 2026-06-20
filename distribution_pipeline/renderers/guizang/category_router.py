from __future__ import annotations


CATEGORY_TABLE = {
    "travel": {
        "label": "旅行",
        "capability": "strong",
        "mode_hint": "editorial",
        "keywords": ("旅行", "旅居", "城市", "目的地", "路线", "行程", "景点", "徒步", "酒店", "民宿", "山野", "海边", "travel", "trip"),
        "editorial": ("M01", "M16", "M02", "M11", "M07"),
        "swiss": ("S01", "S11", "S06", "S07"),
        "deck_sequence": {
            "editorial": ("M01", "M02", "M14", "M02", "M11", "M07"),
            "swiss": ("S01", "S11", "S06", "S07"),
        },
        "scope": "in_scope",
    },
    "workplace": {
        "label": "职场",
        "capability": "strong",
        "mode_hint": "swiss",
        "keywords": ("职场", "工作", "团队", "管理", "效率", "会议", "绩效", "流程", "复盘", "career", "office", "workplace"),
        "editorial": ("M01", "M15", "M14", "M08", "M07"),
        "swiss": ("S01", "S02", "S05", "S06", "S07", "S09", "S11", "S12"),
        "deck_sequence": {
            "editorial": ("M01", "M15", "M14", "M08", "M07"),
            "swiss": ("S01", "S09", "S02", "S05", "S06", "S11", "S07"),
        },
        "scope": "in_scope",
    },
    "game": {
        "label": "游戏",
        "capability": "conditional_image_rights",
        "mode_hint": "editorial",
        "keywords": ("游戏", "通关", "boss", "电竞", "出装", "胜率", "game", "gaming", "elden", "wukong"),
        "editorial": ("M01", "M08", "M15", "M07"),
        "swiss": ("S01", "S07", "S09", "S11"),
        "deck_sequence": {
            "editorial": ("M01", "M08", "M15", "M07"),
            "swiss": ("S01", "S09", "S11", "S07"),
        },
        "scope": "needs_image_rights",
    },
    "film": {
        "label": "影视",
        "capability": "conditional_image_rights",
        "mode_hint": "editorial",
        "keywords": ("电影", "影视", "剧集", "导演", "镜头", "场景", "演员", "film", "movie", "scene"),
        "editorial": ("M04", "M10", "M11", "M07"),
        "swiss": ("S02", "S12", "S07"),
        "deck_sequence": {
            "editorial": ("M04", "M10", "M11", "M07"),
            "swiss": ("S02", "S12", "S07"),
        },
        "scope": "needs_image_rights",
    },
    "food": {
        "label": "美食",
        "capability": "recipes_only",
        "mode_hint": "editorial",
        "keywords": ("美食", "食谱", "烹饪", "菜谱", "食材", "餐厅", "做饭", "recipe", "food"),
        "editorial": ("M16", "M05", "M14", "M02"),
        "swiss": ("S01", "S11", "S06", "S09"),
        "deck_sequence": {
            "editorial": ("M01", "M05", "M14", "M02", "M07"),
            "swiss": ("S01", "S11", "S06", "S09"),
        },
        "scope": "recipes_only",
    },
    "makeup": {
        "label": "彩妆",
        "capability": "tutorial_or_review_only",
        "mode_hint": "swiss",
        "keywords": ("彩妆", "妆容", "口红", "粉底", "色号", "眼影", "makeup", "cosmetic"),
        "editorial": ("M14", "M15", "M02", "M07"),
        "swiss": ("S02", "S11", "S12"),
        "deck_sequence": {
            "editorial": ("M01", "M14", "M15", "M02", "M07"),
            "swiss": ("S02", "S11", "S12"),
        },
        "scope": "tutorial_or_review_only",
    },
    "fitness": {
        "label": "健身",
        "capability": "plans_and_data_only",
        "mode_hint": "swiss",
        "keywords": ("健身", "训练", "跑步", "瑜伽", "肌肉", "力量", "卧推", "fitness", "workout", "running"),
        "editorial": ("M14", "M15", "M07"),
        "swiss": ("S01", "S09", "S11", "S06"),
        "deck_sequence": {
            "editorial": ("M01", "M14", "M15", "M07"),
            "swiss": ("S01", "S09", "S11", "S06"),
        },
        "scope": "plans_and_data_only",
    },
    "home": {
        "label": "家居",
        "capability": "needs_user_photos_for_showcase",
        "mode_hint": "editorial",
        "keywords": ("家居", "装修", "租房", "收纳", "房间", "家具", "home", "interior"),
        "editorial": ("M16", "M15", "M02", "M11"),
        "swiss": ("S01", "S11", "S12"),
        "deck_sequence": {
            "editorial": ("M01", "M15", "M02", "M11", "M07"),
            "swiss": ("S01", "S11", "S12"),
        },
        "scope": "needs_user_photos_for_showcase",
    },
    "fashion": {
        "label": "穿搭",
        "capability": "capsule_or_review_only",
        "mode_hint": "editorial",
        "keywords": ("穿搭", "衣橱", "单品", "服装", "ootd", "fashion", "outfit"),
        "editorial": ("M11", "M04", "M07"),
        "swiss": ("S11", "S12"),
        "deck_sequence": {
            "editorial": ("M01", "M11", "M04", "M07"),
            "swiss": ("S01", "S12", "S11"),
        },
        "scope": "capsule_or_review_only",
    },
    "emotion": {
        "label": "情感",
        "capability": "essay_only",
        "mode_hint": "editorial",
        "keywords": ("情感", "孤独", "孤寂", "独处", "关系", "亲密", "分手", "消失", "alone", "solitude", "disappear"),
        "editorial": ("M04", "M09", "M11", "M13", "M07"),
        "swiss": ("S02", "S07", "S12"),
        "deck_sequence": {
            "editorial": ("M04", "M09", "M11", "M13", "M07"),
            "swiss": ("S02", "S07", "S12"),
        },
        "scope": "essay_only",
    },
    "recommend": {
        "label": "推荐",
        "capability": "needs_subtype",
        "mode_hint": "swiss",
        "keywords": ("推荐", "清单", "好物", "工具", "书单", "测评", "review", "recommend"),
        "editorial": ("M02", "M05", "M11", "M07"),
        "swiss": ("S01", "S11", "S12", "S10"),
        "deck_sequence": {
            "editorial": ("M01", "M02", "M05", "M11", "M07"),
            "swiss": ("S01", "S12", "S11", "S10"),
        },
        "scope": "needs_subtype",
    },
}

# 反向索引：显式标签/中英文别名 → 品类 key（lowercased 比较）
CATEGORY_BY_LABEL = {
    "旅行": "travel", "travel": "travel", "trip": "travel", "journey": "travel",
    "职场": "workplace", "workplace": "workplace", "career": "workplace", "office": "workplace",
    "游戏": "game", "game": "game", "gaming": "game", "games": "game",
    "影视": "film", "电影": "film", "film": "film", "movie": "film", "movies": "film",
    "美食": "food", "food": "food", "recipe": "food", "recipes": "food", "cooking": "food",
    "彩妆": "makeup", "makeup": "makeup", "cosmetics": "makeup", "cosmetic": "makeup",
    "健身": "fitness", "fitness": "fitness", "workout": "fitness", "running": "fitness",
    "家居": "home", "home": "home", "interior": "home", "house": "home",
    "穿搭": "fashion", "fashion": "fashion", "outfit": "fashion", "wardrobe": "fashion",
    "情感": "emotion", "emotion": "emotion", "essay": "emotion",
    "推荐": "recommend", "recommend": "recommend", "review": "recommend", "reviews": "recommend",
}

# 显式标签显式命中时使用的 score 哨兵；用于在调用方判断"用户已点明品类"
EXPLICIT_LABEL_SCORE = 99

# 上游 `category-cookbook.md` Capability Circle 明确不接的子型。
# 命中后返回 key=default + scope=out_of_scope + out_of_scope={key,label,reason}，
# 调用方应在用户面前诚实告知该类超出 skill 范围，并建议改用其他工具。
OUT_OF_SCOPE_SUBTYPES = {
    "dreamcore": {
        "label": "梦核 / Y2K / kawaii 装饰风",
        "keywords": (
            "梦核", "氛围感", "氛围装饰", "y2k", "千禧", "千禧辣妹", "哥特萝莉",
            "kawaii", "aesthetic", "梦核风", "氛围感装饰",
        ),
        "reason": (
            "梦核 / Y2K / kawaii / 氛围感装饰风与 Editorial 与 Swiss 两套视觉系统"
            "正面冲突，硬接会很难看；建议改用专门的装饰风排版工具。"
        ),
    },
    "ootd_body": {
        "label": "穿搭日常 OOTD 全身照",
        "keywords": (
            "ootd 全身", "日常 ootd", "自拍穿搭", "全身穿搭", "穿搭自拍",
            "daily outfit", "全身照穿搭",
        ),
        "reason": (
            "本 skill 不生成或请求人像全身照；日常 OOTD 全身超出能力范围。"
            "建议改用真实拍摄 + 简单排版工具。"
        ),
    },
    "food_showcase": {
        "label": "美食菜品大片摆盘",
        "keywords": (
            "菜品大片", "摆盘大片", "美食大片", "餐厅氛围", "米其林摆盘",
            "菜片拍摄", "food photography",
        ),
        "reason": (
            "本 skill 不替代专业美食摄影；菜品大片摆盘超出能力范围。"
            "建议改用专业摄影 + 简单图说工具。"
        ),
    },
    "photo_essay": {
        "label": "纯摄影秀 / 摄影集",
        "keywords": (
            "摄影集", "摄影秀", "photo essay", "摄影作品", "纯摄影",
            "photography showcase",
        ),
        "reason": (
            "本 skill 是图文排版系统，非纯摄影秀工具。"
            "当图本身就是全部交付物时，超出 skill 范围。"
        ),
    },
}

SCOPE_NOTES = {
    "in_scope": (),
    "needs_image_rights": ("需要用户确认图片版权或提供官方素材。",),
    "recipes_only": ("适合食谱/食物文章；不自动承诺菜品大片摆拍。",),
    "tutorial_or_review_only": ("适合彩妆教程/测评；不自动生成真人妆面。",),
    "plans_and_data_only": ("适合训练计划/数据复盘；进展照需用户提供。",),
    "needs_user_photos_for_showcase": ("展示型家居图需用户照片。",),
    "capsule_or_review_only": ("适合穿搭清单/精选；日常 OOTD 全身照不在自动范围内。",),
    "essay_only": ("适合克制文本卡；梦核/氛围装饰风不在当前视觉系统内。",),
    "needs_subtype": ("推荐类需要底层子类型，默认按清单/测评处理。",),
    "out_of_scope": (),  # 由 detect_rednote_category 在命中 out-of-scope 时填入 reason
}


def _category_text(source: dict, insights: list[dict]) -> str:
    parts = [
        source.get("title", ""),
        source.get("channel", ""),
        " ".join(source.get("tags", [])),
        " ".join(item.get("title", "") for item in insights),
        " ".join(item.get("body", "") for item in insights[:5]),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _explicit_labels(source: dict) -> set[str]:
    """从 source.tags 中抽取已知的品类 key 集合（去重）。"""
    labels: set[str] = set()
    for tag in source.get("tags", []):
        key = CATEGORY_BY_LABEL.get(str(tag or "").strip().lower())
        if key:
            labels.add(key)
    return labels


def _match_out_of_scope(text: str) -> dict | None:
    """在标题/正文/标签汇总文本里检查是否命中任何 out-of-scope 子型。"""
    for key, spec in OUT_OF_SCOPE_SUBTYPES.items():
        if any(kw.lower() in text for kw in spec["keywords"]):
            return {"key": key, "label": spec["label"], "reason": spec["reason"]}
    return None


def _default_response() -> dict:
    return {
        "key": "default",
        "label": "默认",
        "capability": "general",
        "mode_hint": "editorial",
        "editorial": (),
        "swiss": (),
        "deck_sequence": {"editorial": (), "swiss": ()},
        "scope": "in_scope",
        "scope_notes": (),
        "score": 0,
    }


def _build_response(key: str, spec: dict, score: int) -> dict:
    scope = spec.get("scope", "in_scope")
    response = {
        "key": key,
        "label": spec["label"],
        "capability": spec["capability"],
        "mode_hint": spec["mode_hint"],
        "editorial": spec["editorial"],
        "swiss": spec["swiss"],
        "deck_sequence": spec.get("deck_sequence", {"editorial": (), "swiss": ()}),
        "scope": scope,
        "scope_notes": SCOPE_NOTES.get(scope, ()),
        "score": score,
    }
    if scope == "out_of_scope":
        # 当前 SCOPE_NOTES 无该键；保留显式 pushback 文案在 out_of_scope 字段
        response["out_of_scope"] = spec.get("out_of_scope", {})
    return response


def detect_rednote_category(source: dict, insights: list[dict]) -> dict:
    text = _category_text(source, insights)
    explicit = _explicit_labels(source)

    # 1) out-of-scope pushback 优先于品类判定
    oos = _match_out_of_scope(text)
    if oos:
        response = _default_response()
        response["scope"] = "out_of_scope"
        response["scope_notes"] = (oos["reason"],)
        response["out_of_scope"] = oos
        return response

    # 2) 显式标签唯一命中 → 直接采用，跳过关键词打分
    if len(explicit) == 1:
        key = next(iter(explicit))
        spec = CATEGORY_TABLE[key]
        return _build_response(key, spec, EXPLICIT_LABEL_SCORE)

    # 3) 关键词 + 显式标签加权打分
    best_key = "default"
    best_score = 0
    for key, spec in CATEGORY_TABLE.items():
        score = sum(1 for keyword in spec["keywords"] if keyword.lower() in text)
        if key in explicit:
            score += 5
        if score > best_score:
            best_key = key
            best_score = score

    if best_key == "default" or best_score < 2:
        return _default_response()

    spec = CATEGORY_TABLE[best_key]
    return _build_response(best_key, spec, best_score)
