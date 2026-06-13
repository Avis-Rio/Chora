from distribution_pipeline.directors.visual_brief import build_visual_briefs


def test_build_visual_briefs_assigns_unique_metaphors():
    visual_system = {
        "visual_motifs": ["账本", "仪表盘", "天平", "电流"],
        "avoid": ["硬币图标"],
    }
    insights = [
        {"index": 1, "title": "成本结构的范式转移", "body": "AI 产品让推理成为真实成本。"},
        {"index": 2, "title": "计量即权力", "body": "谁定义 Token 的计量方式，谁就定义边界。"},
    ]

    briefs = build_visual_briefs(insights, visual_system)

    assert len(briefs) == 2
    assert briefs[0]["visual_metaphor"] != briefs[1]["visual_metaphor"]
    assert briefs[0]["composition"]["text_position"]
    assert "硬币图标" in briefs[0]["forbidden_cliches"]
