import pytest

from distribution_pipeline.renderers.guizang.recipes import render_page_section


def test_render_editorial_cover_section():
    page = {
        "id": "xhs-01",
        "platform": "xhs",
        "role": "cover",
        "recipe": "M01",
        "title": "Token 经济学正在改写 AI 成本",
        "body": "强模型不只是更贵，也可能更省。",
        "kicker": "Issue 01",
        "footer": "Chora · Rhizomata",
        "title_lines": ["Token 经济学", "AI 成本"],
    }

    html = render_page_section(page, mode="editorial")

    assert 'class="poster xhs"' in html
    assert 'id="xhs-01"' in html
    assert "Token 经济学" in html
    assert "Token 经济学<br>AI 成本" in html
    assert 'class="h-display" style="font-size:92px"' in html
    assert "mag-bg" in html
    assert "paper-wash" in html


def test_render_page_section_escapes_content():
    page = {
        "id": "xhs-01",
        "platform": "xhs",
        "role": "cover",
        "recipe": "M01",
        "title": "<script>alert(1)</script>",
        "body": "正文",
        "kicker": "Issue 01",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_evidence_feature_includes_downloaded_image():
    page = {
        "id": "xhs-02",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M10",
        "title": "视觉理解进入工程阶段",
        "body": "模型不只是看图，而是在把视觉变成可调度的系统能力。",
        "kicker": "Insight 02",
        "footer": "Chora",
        "points": ["视觉能力成为基础设施。", "数据质量决定系统上限。"],
        "image": {
            "src": "assets/images/xhs-02-evidence.png",
            "caption": "AI research lab",
            "object_position": "center 45%",
        },
    }

    html = render_page_section(page, mode="editorial")

    assert "Evidence" in html
    assert 'class="frame-img r-4x3"' in html
    assert 'src="assets/images/xhs-02-evidence.png"' in html
    assert "AI research lab" in html


def test_render_evidence_feature_does_not_repeat_lead_in_rows():
    page = {
        "id": "xhs-08",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M10",
        "title": "视觉推理的空白地带",
        "body": "递归自我提升驱使大公司押注编程。这反而为视觉推理创造窗口。",
        "kicker": "Insight 07",
        "footer": "Chora",
        "points": ["递归自我提升驱使大公司押注编程", "这反而为视觉推理创造窗口。"],
        "image": {
            "src": "assets/images/xhs-08-evidence.svg",
            "caption": "computer vision lab",
        },
    }

    html = render_page_section(page, mode="editorial")

    assert html.count("递归自我提升驱使大公司押注编程") == 1
    assert "ledger-title\">这反而为视觉推理创造窗口。" in html
    assert "ledger-note\">注记" not in html
    assert "注记" not in html


def test_render_field_note_photo_uses_large_image_column():
    page = {
        "id": "xhs-04",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M02",
        "title": "第三空间的政治经济学",
        "body": "公共空间的消失不是自然发生的，而是城市规划、资本逻辑和个人主义文化共同作用的结果。",
        "kicker": "Insight 03",
        "footer": "Chora",
        "image": {
            "src": "assets/images/xhs-04-evidence.jpg",
            "caption": "quiet city cafe library",
            "object_position": "center 45%",
        },
    }

    html = render_page_section(page, mode="editorial")

    assert "FIELD 04" in html
    assert 'class="frame-img r-3x4"' in html
    assert 'src="assets/images/xhs-04-evidence.jpg"' in html


def test_render_checklist_uses_numbered_rows():
    page = {
        "id": "xhs-05",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M05",
        "title": "增长靠两种习惯",
        "body": "把行动拆成可重复步骤。",
        "kicker": "Insight 04",
        "footer": "Chora",
        "items": [
            {"index": "01", "title": "验证内容", "note": "先在小范围看反馈。"},
            {"index": "02", "title": "真实社交", "note": "用互惠建立连接。"},
            {"index": "03", "title": "固定节奏", "note": "减少临场决策。"},
            {"index": "04", "title": "记录结果", "note": "让复盘有材料。"},
        ],
    }

    html = render_page_section(page, mode="editorial")

    assert "Checklist" in html
    assert "验证内容" in html
    assert "固定节奏" in html
    assert "min-height:680px" in html


def test_render_evidence_wall_uses_multi_image_grid():
    page = {
        "id": "xhs-06",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M06",
        "title": "证据不是一张图",
        "body": "多张图共同构成语境。",
        "kicker": "Insight 05",
        "footer": "Chora",
        "images": [
            {"src": "assets/images/a.jpg", "caption": "A"},
            {"src": "assets/images/b.jpg", "caption": "B"},
            {"src": "assets/images/c.jpg", "caption": "C"},
        ],
    }

    html = render_page_section(page, mode="editorial")

    assert "Evidence Wall" in html
    assert html.count('class="frame-img r-4x3"') == 3
    assert "E01" in html
    assert "E03" in html


def test_render_section_divider_uses_big_act_title():
    page = {
        "id": "xhs-07",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M12",
        "title": "第二幕",
        "body": "从现象进入机制。",
        "kicker": "Act II · Part 2",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert "Act II · Part 2" in html
    assert "第二幕" in html
    assert "rule-accent" in html


def test_render_before_after_uses_stacked_blocks():
    page = {
        "id": "xhs-08",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M15",
        "title": "旧方式不是答案，新路径才是杠杆",
        "body": "对比不是装饰，而是解释结构。",
        "kicker": "Before · After",
        "footer": "Chora",
        "comparison": {
            "before": {"title": "旧方式", "bullets": ["等待算法", "只看播放量"]},
            "after": {"title": "新路径", "bullets": ["先验证内容", "主动建立连接"]},
        },
    }

    html = render_page_section(page, mode="editorial")

    assert "beforeafter" in html
    assert "ba-block before" in html
    assert "旧方式" in html
    assert "新路径" in html


def test_render_before_after_extracts_not_but_title():
    page = {
        "id": "xhs-03",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M15",
        "title": "优先级漂移，比技术落后更危险。",
        "original_title": "大公司的最大风险不是技术落后，而是优先级漂移。",
        "body": "谷歌拥有几乎所有关键技术的原始版本。但每一次都在最关键的时刻把资源调走。",
        "kicker": "Insight 02",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert "Before · 误判" in html
    assert "技术落后" in html
    assert "After · 真因" in html
    assert "优先级漂移" in html
    assert "注记" not in html


def test_render_image_led_cover_requires_subject_map():
    page = {
        "id": "xhs-01",
        "platform": "xhs",
        "role": "cover",
        "recipe": "M16",
        "title": "在山里重新校准时间",
        "body": "Field notes",
        "kicker": "Cover · Image Led",
        "footer": "Chora",
        "title_lines": ["在山里", "校准时间"],
        "image": {
            "src": "assets/images/hero.jpg",
            "caption": "mountain at dawn",
            "object_position": "center 35%",
            "subject_map": {
                "focus": "mountain peak at 50% x 32% y",
                "safe_zone": "top sky and bottom water",
                "quiet_zone": "PASS",
                "light": "PASS",
            },
        },
    }

    html = render_page_section(page, mode="editorial")

    assert "hero-bleed" in html
    assert "subject map" in html
    assert "background-image:url('assets/images/hero.jpg')" in html
    assert "#f5f1e8" in html


def test_render_editorial_essay_single_sentence_does_not_duplicate_body():
    page = {
        "id": "xhs-03",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M03",
        "title": "技术时机",
        "body": "知识不会自动变成力量。",
        "kicker": "Insight 02",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert html.count("知识不会自动变成力量。") == 1
    assert "density-panel" in html
    assert "Insight Field" in html


def test_render_marginalia_uses_source_text_instead_of_generated_labels():
    page = {
        "id": "xhs-04",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M11",
        "title": "组织漂移",
        "body": "资源无限并不等于方向稳定。优先级漂移会吃掉技术窗口。",
        "kicker": "Insight 03",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert html.count("资源无限并不等于方向稳定。") == 1
    assert "sparse-thesis" in html
    assert "组织" in html
    assert "Margin Notes" in html
    assert "density-panel" not in html
    assert "注记" not in html
    assert "脉络" not in html


def test_render_atmospheric_thesis_uses_accent_number_and_callout():
    page = {
        "id": "xhs-09",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M09",
        "title": "研究品位的本质是时间管理。",
        "body": "判断哪个方向值得追，比执行能力更重要。",
        "kicker": "Insight 08",
        "footer": "Chora",
        "display_index": "08",
    }

    html = render_page_section(page, mode="editorial")

    assert "Point 08" in html
    assert "rgba(var(--accent-rgb),.14)" in html
    assert "核心判断" in html
    assert '<span style="color:var(--accent)">研究品位</span>的本质是时间管理。' in html


def test_render_hero_question_for_philosophy():
    page = {
        "id": "xhs-12",
        "platform": "xhs",
        "role": "philosophy",
        "recipe": "M13",
        "title": "时间不可逆",
        "body": "知识不会自动变成力量。它需要一个人押上自己的时间。",
        "kicker": "Philosophical Epilogue",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert "What remains after the argument." in html
    assert '<span style="color:var(--accent)">时间不可逆</span>' in html
    assert "density-panel" in html
    assert "Epilogue Field" in html


def test_render_sparse_pipeline_as_flowing_prose_without_generated_labels():
    page = {
        "id": "xhs-10",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M14",
        "title": "硅谷的知识流动是双向的。",
        "body": "人才和知识在大公司与创业公司之间流动。",
        "kicker": "Insight 09",
        "footer": "Chora",
        "points": ["人才进入大公司。", "经验回流创业公司。"],
    }

    html = render_page_section(page, mode="editorial")

    assert "structure-prose" in html
    assert "pipeline-v" not in html
    assert "Structure Field" not in html
    assert "人才和知识在大公司与创业公司之间流动。" in html
    assert "机制" not in html
    assert "代价" not in html


def test_render_pipeline_keeps_explicit_items_structured():
    page = {
        "id": "xhs-04",
        "platform": "xhs",
        "role": "concept-map",
        "recipe": "M14",
        "title": "从数据到能力",
        "body": "结构化流程。",
        "kicker": "Structure",
        "footer": "Chora",
        "items": [
            {"index": "01", "title": "采集", "note": "数据进入系统。"},
            {"index": "02", "title": "清洗", "note": "噪声被移除。"},
            {"index": "03", "title": "训练", "note": "能力被固化。"},
        ],
    }

    html = render_page_section(page, mode="editorial")

    assert "pipeline-v" in html
    assert "采集" in html
    assert "清洗" in html


def test_render_short_ledger_uses_tall_layout_and_density_panel():
    page = {
        "id": "xhs-03",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M08",
        "title": "组织风险",
        "body": "优先级漂移会吃掉技术窗口。",
        "kicker": "Insight 02",
        "footer": "Chora",
        "items": [
            {"index": "01", "title": "机制", "note": "资源多不等于方向稳。"},
            {"index": "02", "title": "代价", "note": "协作成本被低估。"},
        ],
    }

    html = render_page_section(page, mode="editorial")

    assert "min-height:520px" in html
    assert "density-panel" in html
    assert "Ledger Field" in html
    assert "Archive Index" not in html


def test_render_closing_note_uses_dedicated_layout_without_archive_index():
    page = {
        "id": "xhs-13",
        "platform": "xhs",
        "role": "closing",
        "recipe": "M07",
        "title": "完整内容见 Chora",
        "body": "关注 Rhizomata，获取更多深度内容与延伸阅读。",
        "kicker": "Closing Note",
        "footer": "Chora",
        "items": [
            {"index": "01", "title": "技术的时机比技术本身更重要。", "note": "note"},
            {"index": "02", "title": "大公司的最大风险不是技术落后。", "note": "note"},
            {"index": "03", "title": "数据是最不透明的差异点。", "note": "note"},
            {"index": "04", "title": "不会被渲染进拥挤底部。", "note": "note"},
        ],
    }

    html = render_page_section(page, mode="editorial")

    assert "closing-mark" in html
    assert "read the full issue" in html
    assert "Archive Index" not in html
    assert "density-panel" not in html
    assert "不会被渲染进拥挤底部" not in html


def test_render_closing_note_includes_subtle_cta_strip():
    page = {
        "id": "xhs-08",
        "platform": "xhs",
        "role": "closing",
        "recipe": "M07",
        "title": "读完整篇前，先带走这三点",
        "title_lines": ["读完整篇前先带走这三点"],
        "body": "卡片之外还有完整上下文。",
        "kicker": "Closing Note",
        "footer": "Chora",
        "items": [{"index": "01", "title": "判断比结论重要。", "note": "note"}],
        "cta": {
            "label": "阅读全文",
            "site_label": "Chora",
            "url": "https://example.com",
            "qr_label": "公众号 · Rhizomata",
            "qr_src": "assets/brand/rhizomata-qr.png",
        },
    }

    html = render_page_section(page, mode="editorial")

    assert "cta-strip" in html
    assert "读完整篇前</span><br>" in html
    assert "先带走这三点" in html
    assert "example.com" in html
    assert "https://example.com" not in html
    assert 'src="assets/brand/rhizomata-qr.png"' in html
    assert "公众号 · Rhizomata" in html
    assert "关注 Rhizomata" in html
    assert "长按识别" not in html
    assert 'class="issue-strip" style="border-top:0;padding-top:0"' in html


def test_render_swiss_closing_embeds_cta_in_final_field_card():
    page = {
        "id": "xhs-05",
        "platform": "xhs",
        "role": "closing",
        "recipe": "S07",
        "title": "完整内容见 Chora",
        "body": "关注 Rhizomata，获取更多深度内容与延伸阅读。",
        "kicker": "Closing Note",
        "footer": "Chora",
        "display_index": "05",
        "items": [{"index": "01", "title": "判断比结论重要。", "note": "note"}],
        "cta": {
            "label": "阅读全文",
            "site_label": "Chora",
            "url": "https://chora.avisionary.top",
            "qr_label": "公众号 · Rhizomata",
            "qr_src": "assets/brand/rhizomata-qr.png",
        },
    }

    html = render_page_section(page, mode="swiss")

    assert "Takeaway · Ledger" in html
    assert "<h2 class=\"h-xl\">完整内容见 Chora</h2>" in html
    assert "CHORA ARCHIVE" in html
    assert "archive-mark" in html
    assert "<svg" in html
    assert "完整文章与延伸阅读" not in html
    assert "FINAL FIELD" not in html
    assert "cta-marker" in html
    assert "cta-strip" not in html
    assert "WWW.CHORA.AVISIONARY.TOP" in html
    assert "https://chora.avisionary.top" not in html
    assert 'src="assets/brand/rhizomata-qr.png"' in html
    assert "关注 Rhizomata" in html


def test_render_swiss_closing_breaks_long_tail_title_semantically():
    page = {
        "id": "xhs-05",
        "platform": "xhs",
        "role": "closing",
        "recipe": "S07",
        "title": "读完整篇前，先带走这三点",
        "title_lines": ["读完整篇前先带走这三点"],
        "body": "卡片之外还有完整上下文。",
        "kicker": "Closing Note",
        "footer": "Chora",
        "display_index": "05",
        "items": [{"index": "01", "title": "判断比结论重要。", "note": "note"}],
        "cta": {"url": "https://chora.avisionary.top"},
    }

    html = render_page_section(page, mode="swiss")

    assert "读完整篇前<br>先带走这三点" in html


def test_render_accent_title_keeps_latin_phrase_together():
    page = {
        "id": "xhs-11",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M09",
        "title": "Neo Lab的窗口期是有限的。",
        "body": "窗口期可能只有两年左右。",
        "kicker": "Insight 10",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert '<span style="color:var(--accent)">Neo Lab</span>的窗口期是有限的。' in html


def test_render_accent_title_keeps_chinese_phrase_together():
    page = {
        "id": "xhs-06",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M09",
        "title": "合成数据是双刃剑。",
        "body": "质量控制决定它是能力放大器还是偏差放大器。",
        "kicker": "Insight 05",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert '<span style="color:var(--accent)">合成数据</span>是双刃剑。' in html
    assert "合成数据是双</span>刃剑" not in html


def test_render_accent_title_splits_before_structural_verb():
    page = {
        "id": "xhs-02",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M09",
        "title": "视觉理解进入工程阶段",
        "body": "视觉能力正在成为系统能力。",
        "kicker": "Insight 01",
        "footer": "Chora",
    }

    html = render_page_section(page, mode="editorial")

    assert '<span style="color:var(--accent)">视觉理解</span>进入工程阶段' in html


def test_render_page_section_rejects_wrong_recipe_family():
    page = {
        "id": "xhs-01",
        "platform": "xhs",
        "role": "cover",
        "recipe": "S01",
        "title": "标题",
        "body": "正文",
    }

    with pytest.raises(ValueError, match="does not match guizang mode"):
        render_page_section(page, mode="editorial")


@pytest.mark.parametrize(
    ("recipe", "snippet"),
    [
        ("S01", "Cover · Rednote"),
        ("S02", "Two Signals · Comparison"),
        ("S03", "Data Layer · File Card"),
        ("S04", "device-browser"),
        ("S05", "Trap · Warning Rows"),
        ("S06", "Pipeline · Architecture"),
        ("S07", "Takeaway · Ledger"),
        ("S08", "image-hero"),
        ("S09", "kpi-tower-row"),
        ("S10", "h-bar-chart"),
        ("S11", "stacked-ledger"),
        ("S12", "matrix-fill"),
    ],
)
def test_render_swiss_recipe_family_uses_distinct_structures(recipe, snippet):
    page = {
        "id": "xhs-02",
        "platform": "xhs",
        "role": "insight",
        "recipe": recipe,
        "title": "增长不是等待算法，而是建立系统",
        "body": "第一步记录问题。第二步发布观察。第三步主动反馈。第四步复盘下一次表达。",
        "kicker": "Insight 01",
        "footer": "Chora",
        "display_index": "01",
        "points": ["记录问题。", "发布观察。", "主动反馈。", "复盘表达。"],
        "items": [
            {"index": "01", "title": "记录问题", "note": "让素材有来源。"},
            {"index": "02", "title": "发布观察", "note": "让判断接受反馈。"},
            {"index": "03", "title": "主动反馈", "note": "让连接先发生。"},
            {"index": "04", "title": "复盘表达", "note": "让系统可迭代。"},
        ],
        "image": {
            "src": "assets/images/hero.jpg",
            "caption": "system board",
            "object_position": "center 40%",
            "subject_map": {
                "focus": "center board",
                "safe_zone": "lower-left",
                "quiet_zone": "left band",
                "light": "restrained",
            },
        },
    }

    html = render_page_section(page, mode="swiss")

    assert 'class="poster xhs"' in html
    assert snippet in html
    assert "mag-bg" not in html
    assert "serif" not in html


def test_render_editorial_fallback_items_do_not_emit_scaffold_labels():
    page = {
        "id": "xhs-03",
        "platform": "xhs",
        "role": "insight",
        "recipe": "M08",
        "title": "孤独的历史性转变",
        "body": "第一层是社会空间的撤退。第二层是数字连接的错觉。第三层是身份表达的疲惫。",
        "kicker": "Insight 02",
        "footer": "Chora",
        "points": ["社会空间正在撤退。", "数字连接制造错觉。", "身份表达变得疲惫。"],
    }

    html = render_page_section(page, mode="editorial")

    for label in ("注记", "脉络", "张力", "信号", "余波", "边界", "后果"):
        assert label not in html
    assert "社会空间正在撤退。" in html
    assert "数字连接制造错觉。" in html


def test_render_swiss_fallback_items_do_not_emit_scaffold_labels():
    page = {
        "id": "xhs-03",
        "platform": "xhs",
        "role": "insight",
        "recipe": "S04",
        "title": '"越贵越便宜"的悖论',
        "body": "在 agent 场景下，模型的单价不等于任务的综合成本。强模型一次完成，弱模型反复送代。",
        "kicker": "Insight 02",
        "footer": "Chora",
        "display_index": "02",
        "points": [
            "在 agent 场景下，模型的单价不等于任务的综合成本。",
            "强模型一次完成，弱模型反复送代。",
            "评估 AI 成本必须以有效结论为单位。",
        ],
        "items": [],
    }

    html = render_page_section(page, mode="swiss")

    for label in ("注记", "脉络", "张力", "信号", "余波", "边界", "后果"):
        assert label not in html
    assert "在 agent 场景下" in html
    assert "强模型一次完成" in html


def test_render_swiss_interface_uses_copy_slots_without_repeating_lead():
    page = {
        "id": "xhs-04",
        "platform": "xhs",
        "role": "insight",
        "recipe": "S04",
        "title": "成本结构的范式转移",
        "body": "传统 SaaS 的边际成本趋近于零。AI 时代的成本随用量线性增长。这会重写商业模式。",
        "kicker": "Insight 01",
        "footer": "Chora",
        "display_index": "01",
        "points": [
            "传统 SaaS 的边际成本趋近于零。",
            "AI 时代的成本随用量线性增长。",
            "这会重写商业模式。",
        ],
        "items": [],
    }

    html = render_page_section(page, mode="swiss")

    assert html.count("传统 SaaS 的边际成本趋近于零。") == 1
    assert html.count("AI 时代的成本随用量线性增长。") == 1
    assert html.count("这会重写商业模式。") == 1


def test_render_swiss_takeaway_ledger_does_not_repeat_lead_in_rows():
    page = {
        "id": "xhs-07",
        "platform": "xhs",
        "role": "insight",
        "recipe": "S07",
        "title": "Token 是新形态的大宗商品",
        "body": "黄仁勋的判断正在被验证。商业模式会重演。速度快了几个数量级。",
        "kicker": "Insight 05",
        "footer": "Chora",
        "display_index": "05",
        "points": [
            "黄仁勋的判断正在被验证。",
            "商业模式会重演。",
            "速度快了几个数量级。",
        ],
        "items": [],
    }

    html = render_page_section(page, mode="swiss")

    assert html.count("黄仁勋的判断正在被验证。") == 1


def test_render_swiss_interface_consumes_non_overlay_evidence_image():
    page = {
        "id": "xhs-02",
        "platform": "xhs",
        "role": "insight",
        "recipe": "S04",
        "title": "证据图进入页面主体",
        "body": "没有 subject map 的图片不能做图上叠字，但仍应作为证据图进入页面。",
        "kicker": "Insight 01",
        "footer": "Chora",
        "display_index": "01",
        "points": ["没有 subject map 的图片不能做图上叠字。", "证据图应进入页面主体。"],
        "image": {
            "src": "assets/images/xhs-02-evidence.png",
            "caption": "AI compute data center",
            "object_position": "center 50%",
        },
    }

    html = render_page_section(page, mode="swiss")

    assert 'src="assets/images/xhs-02-evidence.png"' in html
    assert "image-hero" not in html
    assert html.count("没有 subject map 的图片不能做图上叠字。") >= 1
    assert html.count("证据图进入页面主体") >= 1


def test_render_swiss_takeaway_ledger_does_not_repeat_reader_takeaway_lead():
    page = {
        "id": "xhs-07",
        "platform": "xhs",
        "role": "insight",
        "recipe": "S07",
        "title": "传记作为文化史",
        "body": "约瑟夫·弗兰克的传记写作示范了如何通过一个作家的生命，透视整个时代的精神结构。个体痛苦被转化为理解民族精神危机的钥匙。",
        "reader_takeaway": "约瑟夫·弗兰克的传记写作示范了如何通过一个作家的生命，透视整个时代的精神结构。",
        "kicker": "Insight 06",
        "footer": "Chora",
        "display_index": "06",
        "points": [
            "约瑟夫·弗兰克的传记写作示范了如何通过一个作家的生命，透视整个时代的精神结构。",
            "个体痛苦被转化为理解民族精神危机的钥匙。",
        ],
        "items": [],
    }

    html = render_page_section(page, mode="swiss")

    assert html.count("约瑟夫·弗兰克的传记写作示范了如何通过一个作家的生命，透视整个时代的精神结构。") == 1


def test_render_swiss_hbar_uses_extracted_metric_labels():
    page = {
        "id": "xhs-02",
        "platform": "xhs",
        "role": "insight",
        "recipe": "S10",
        "title": "成本下降 20% 才是真指标",
        "body": "团队用 3 周把返工率从 18% 降到 9%。",
        "kicker": "Insight 01",
        "footer": "Chora",
        "display_index": "01",
        "metric_tokens": [
            {"raw": "20%", "value": 20, "source": "extracted"},
            {"raw": "3周", "value": 3, "source": "extracted"},
        ],
        "items": [
            {"index": "01", "title": "成本", "note": "下降才是结果。"},
            {"index": "02", "title": "周期", "note": "三周内完成。"},
        ],
    }

    html = render_page_section(page, mode="swiss")

    assert "20%" in html
    assert "3周" in html
    assert 'data-metric-source="extracted"' in html
    assert "20字" not in html


def test_render_swiss_hbar_does_not_emit_proxy_placeholders():
    page = {
        "id": "xhs-04",
        "platform": "xhs",
        "role": "insight",
        "recipe": "S10",
        "title": "三个信号正在合流",
        "body": "成本、渠道和组织节奏正在互相影响。",
        "kicker": "Insight 03",
        "footer": "Chora",
        "display_index": "03",
        "items": [
            {"index": "01", "title": "成本", "note": "调用智能的门槛下降。"},
            {"index": "02", "title": "渠道", "note": "分发方式改变产品形态。"},
        ],
    }

    html = render_page_section(page, mode="swiss")

    assert "P01" not in html
    assert "P02" not in html
    assert "rank 01" in html
    assert 'data-metric-source="proxy"' in html


def test_render_page_section_rejects_unknown_swiss_recipe():
    page = {
        "id": "xhs-01",
        "platform": "xhs",
        "role": "cover",
        "recipe": "S99",
        "title": "标题",
        "body": "正文",
    }

    with pytest.raises(ValueError, match="Unsupported swiss recipe"):
        render_page_section(page, mode="swiss")
