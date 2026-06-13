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
            "swiss": ("S02", "S12", "S07"),
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


def detect_rednote_category(source: dict, insights: list[dict]) -> dict:
    text = _category_text(source, insights)
    explicit_tags = {str(tag).lower() for tag in source.get("tags", [])}
    best_key = "default"
    best_score = 0
    for key, spec in CATEGORY_TABLE.items():
        score = sum(1 for keyword in spec["keywords"] if keyword.lower() in text)
        if spec["label"].lower() in explicit_tags or key in explicit_tags:
            score += 3
        if score > best_score:
            best_key = key
            best_score = score

    if best_key == "default" or best_score < 2:
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

    spec = CATEGORY_TABLE[best_key]
    scope = spec.get("scope", "in_scope")
    return {
        "key": best_key,
        "label": spec["label"],
        "capability": spec["capability"],
        "mode_hint": spec["mode_hint"],
        "editorial": spec["editorial"],
        "swiss": spec["swiss"],
        "deck_sequence": spec.get("deck_sequence", {"editorial": (), "swiss": ()}),
        "scope": scope,
        "scope_notes": SCOPE_NOTES.get(scope, ()),
        "score": best_score,
    }
