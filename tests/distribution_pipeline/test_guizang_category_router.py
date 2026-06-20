from distribution_pipeline.renderers.guizang.category_router import detect_rednote_category


def test_detect_rednote_category_uses_tags_title_and_insights():
    source = {"title": "三天两夜云南旅行路线", "channel": "Chora", "tags": ["旅行", "路线"]}
    insights = [{"title": "第一天先去古城", "body": "把行程压到可步行范围。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "travel"
    assert category["label"] == "旅行"
    assert "M02" in category["editorial"]
    assert category["scope"] == "in_scope"
    assert category["deck_sequence"]["editorial"][1] == "M02"


def test_detect_rednote_category_marks_workplace_as_swiss_first():
    source = {"title": "职场复盘系统", "channel": "Chora", "tags": ["效率"]}
    insights = [{"title": "流程决定复利", "body": "团队管理不是靠临场发挥。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "workplace"
    assert category["mode_hint"] == "swiss"
    assert "S06" in category["swiss"]
    assert category["deck_sequence"]["swiss"][1] == "S09"


def test_detect_rednote_category_surfaces_scope_notes_for_image_rights():
    source = {"title": "Elden Ring boss 战复盘", "channel": "Chora", "tags": ["游戏"]}
    insights = [{"title": "胜率不是唯一指标", "body": "通关体验来自路线和资源管理。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "game"
    assert category["scope"] == "needs_image_rights"
    assert category["scope_notes"]


def test_detect_rednote_category_ignores_single_generic_keyword():
    source = {"title": "谷歌 AI 的技术路线", "channel": "硅谷101"}
    insights = [{"title": "研究品位的本质是时间管理。", "body": "判断比执行更重要。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "default"


# -----------------------------------------------------------------------------
# 乙项扩类（vendor/references/category-cookbook.md 11 类 + pushback）测试
# -----------------------------------------------------------------------------


def test_detect_rednote_category_handles_film_with_scope_notes():
    source = {"title": "诺兰新片镜头语言拆解", "channel": "Chora", "tags": ["影视"]}
    insights = [{"title": "长镜头与配乐", "body": "IMAX 场景的拍摄节奏与导演意志。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "film"
    assert category["label"] == "影视"
    assert category["scope"] == "needs_image_rights"
    assert "需要用户确认图片版权" in category["scope_notes"][0]
    assert "M04" in category["editorial"]
    assert category["deck_sequence"]["editorial"][0] == "M04"


def test_detect_rednote_category_handles_food_recipe_subtype():
    source = {"title": "周末家庭菜谱：三道快手家常", "channel": "Chora", "tags": ["美食"]}
    insights = [{"title": "食材采购清单", "body": "三道家常食谱，30 分钟出锅。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "food"
    assert category["scope"] == "recipes_only"
    assert "食谱" in category["scope_notes"][0]
    assert "M05" in category["editorial"]
    assert "M14" in category["editorial"]


def test_detect_rednote_category_handles_makeup_tutorial():
    source = {"title": "新手眼影教程：四色叠加", "channel": "Chora", "tags": ["彩妆"]}
    insights = [{"title": "色号选择", "body": "粉底色号匹配冷暖皮。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "makeup"
    assert category["scope"] == "tutorial_or_review_only"
    assert category["mode_hint"] == "swiss"
    assert "S11" in category["swiss"]


def test_detect_rednote_category_handles_fitness_plans():
    source = {"title": "三月增肌计划：胸背腿分训", "channel": "Chora", "tags": ["健身"]}
    insights = [{"title": "训练量", "body": "每周力量训练四次，跑步两次。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "fitness"
    assert category["scope"] == "plans_and_data_only"
    assert category["mode_hint"] == "swiss"
    assert "S09" in category["swiss"]  # 训练量数字
    assert "S11" in category["swiss"]  # 计划清单


def test_detect_rednote_category_handles_home_needs_user_photos():
    source = {"title": "10 平出租屋改造方案", "channel": "Chora", "tags": ["家居"]}
    insights = [{"title": "收纳分区", "body": "家具布局按功能划分房间。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "home"
    assert category["scope"] == "needs_user_photos_for_showcase"
    assert "M16" in category["editorial"]  # 家居常用满版图
    assert category["deck_sequence"]["editorial"][0] == "M01"


def test_detect_rednote_category_handles_fashion_capsule_essay():
    source = {"title": "今年夏天的胶囊衣橱：6 件基础款", "channel": "Chora", "tags": ["穿搭"]}
    insights = [{"title": "衣橱清理", "body": "服装搭配按气候和生活场景重新组织。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "fashion"
    assert category["scope"] == "capsule_or_review_only"
    assert category["mode_hint"] == "editorial"
    assert "M11" in category["editorial"]  # marginalia essay


def test_detect_rednote_category_handles_emotion_essay():
    source = {"title": "在城市里学会独处", "channel": "Chora", "tags": ["情感"]}
    insights = [{"title": "独处是关系的前提", "body": "孤独不等于孤寂。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "emotion"
    assert category["scope"] == "essay_only"
    assert "M04" in category["editorial"]  # pull quote
    assert "M13" in category["editorial"]  # hero question
    assert category["deck_sequence"]["editorial"][0] == "M04"


def test_detect_rednote_category_handles_recommend_catchall():
    source = {"title": "本月我读过的三本书", "channel": "Chora", "tags": ["推荐", "书单"]}
    insights = [{"title": "推荐理由", "body": "三本书分别讲效率、孤独、组织。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "recommend"
    assert category["scope"] == "needs_subtype"
    assert "需要底层子类型" in category["scope_notes"][0]
    assert "S12" in category["swiss"]  # matrix
    assert "S11" in category["swiss"]  # ledger


# --- 显式标签（EXPLICIT_LABEL_SCORE）路径 ---

def test_detect_rednote_category_uses_explicit_label_even_when_keywords_diverge():
    source = {"title": "我家咖啡角的装修", "channel": "Chora", "tags": ["家居"]}
    # 关键词会同时命中 "home"（家居）和可能的 "fashion"（单品/ootd）或 "food"（咖啡）
    insights = [{"title": "咖啡机单品", "body": "单品置物架。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "home"
    assert category["score"] == 99  # 显式标签 sentinel


def test_detect_rednote_category_uses_english_explicit_label():
    source = {"title": "Q3 product review", "channel": "Chora", "tags": ["review"]}
    insights = [{"title": "Pros and cons", "body": "Compared with last quarter. " * 5}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "recommend"


# --- out-of-scope pushback ---

def test_detect_rednote_category_pushes_back_on_dreamcore():
    source = {"title": "Y2K 千禧辣妹卧室合集", "channel": "Chora", "tags": []}
    insights = [{"title": "kawaii 摆件", "body": "氛围感装饰细节。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "default"
    assert category["scope"] == "out_of_scope"
    assert "out_of_scope" in category
    assert category["out_of_scope"]["key"] == "dreamcore"
    assert "Editorial 与 Swiss" in category["scope_notes"][0]


def test_detect_rednote_category_pushes_back_on_ootd_body():
    source = {"title": "今日 ootd 全身", "channel": "Chora", "tags": ["穿搭"]}
    insights = [{"title": "自拍穿搭", "body": "全身穿搭自拍。"}]

    category = detect_rednote_category(source, insights)

    assert category["scope"] == "out_of_scope"
    assert category["out_of_scope"]["key"] == "ootd_body"
    assert "人像全身照" in category["scope_notes"][0]


def test_detect_rednote_category_pushes_back_on_food_showcase():
    source = {"title": "米其林摆盘菜品大片", "channel": "Chora", "tags": ["美食"]}
    insights = [{"title": "美食大片", "body": "餐厅氛围拍摄。"}]

    category = detect_rednote_category(source, insights)

    assert category["scope"] == "out_of_scope"
    assert category["out_of_scope"]["key"] == "food_showcase"
    assert "专业美食摄影" in category["scope_notes"][0]


def test_detect_rednote_category_pushes_back_on_photo_essay():
    source = {"title": "城市摄影集", "channel": "Chora", "tags": ["摄影集"]}
    insights = [{"title": "摄影作品", "body": "photo essay 摄影秀。"}]

    category = detect_rednote_category(source, insights)

    assert category["scope"] == "out_of_scope"
    assert category["out_of_scope"]["key"] == "photo_essay"


# --- 默认 fallthrough 边界 ---

def test_detect_rednote_category_returns_clean_default_when_no_signal():
    source = {"title": "随笔", "channel": "Chora", "tags": []}
    insights = [{"title": "今天天气不错", "body": "散步时想到一些事。"}]

    category = detect_rednote_category(source, insights)

    assert category["key"] == "default"
    assert category["score"] == 0
    assert category["editorial"] == ()
    assert category["swiss"] == ()


def test_detect_rednote_category_explicit_label_collision_falls_back_to_score():
    """多个显式标签同时出现：不应被唯一路径误锁，按 score 决断。"""
    source = {"title": "AI 与职场效率", "channel": "Chora", "tags": ["职场", "推荐"]}
    insights = [{"title": "AI 工具盘点", "body": "团队管理与效率系统。"}]

    category = detect_rednote_category(source, insights)

    # 两个显式标签都被显式 score+5，按文本 score 决断
    assert category["key"] in {"workplace", "recommend"}
    assert category["score"] != 99  # 没走 EXPLICIT_LABEL_SCORE 路径
