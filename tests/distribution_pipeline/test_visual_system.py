from distribution_pipeline.directors.visual_system import build_visual_system


def test_build_visual_system_returns_motifs_and_constraints():
    source = {
        "title": "Token经济学：AI时代的新货币战争",
        "tags": ["Technology", "Economics", "Power & Politics"],
        "channel": "硅谷101",
    }
    insights = [
        {"title": "计量即权力", "body": "谁定义 Token 的计量方式，谁就定义 AI 经济的边界。"}
    ]

    system = build_visual_system(source, insights)

    assert system["theme"]
    assert len(system["visual_motifs"]) >= 4
    assert "avoid" in system
    assert "composition_rules" in system
