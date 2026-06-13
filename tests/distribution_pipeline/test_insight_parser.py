from pathlib import Path

from distribution_pipeline.extractors.insight_parser import (
    parse_insights,
    parse_philosophical_epilogue,
    parse_tags,
)


def test_parse_insights_from_core_insights_section():
    path = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/rewritten.md")

    insights = parse_insights(path)

    assert len(insights) == 8
    assert insights[0]["index"] == 1
    assert insights[0]["title"] == "成本结构的范式转移"
    assert "边际成本" in insights[0]["body"]
    assert "商业模式逻辑" in insights[0]["body"]
    assert insights[3]["title"] == "计量即权力"
    assert "Metronome" in insights[3]["body"]
    assert insights[7]["title"] == "Token 效率是下一个主战场"
    assert "少烧冤枉钱" in insights[7]["body"]


def test_parse_tags_from_rewritten_file():
    path = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/rewritten.md")

    assert parse_tags(path) == ["Technology", "Economics", "Power & Politics"]


def test_parse_insight_with_bold_title_and_plain_body(tmp_path):
    rewritten = tmp_path / "rewritten.md"
    rewritten.write_text(
        """## 3. 核心洞察 (Core Insights)

1. **技术的时机比技术本身更重要。** 预训练的思想很早就有了，但真正关键的是行动窗口。

## 4. 哲思结语
""",
        encoding="utf-8",
    )

    insights = parse_insights(rewritten)

    assert insights[0]["title"] == "技术的时机比技术本身更重要。"
    assert insights[0]["body"] == "预训练的思想很早就有了，但真正关键的是行动窗口。"


def test_parse_insight_merges_wrapped_body_lines(tmp_path):
    rewritten = tmp_path / "rewritten.md"
    rewritten.write_text(
        """## 3. 核心洞察 (Core Insights)

1. **成本结构的范式转移**：传统 SaaS 的边际成本趋近于零。
这不只是财务问题，而是商业模式逻辑的变化。
2. **计量即权力**：谁掌握计量，谁掌握边界。

## 4. 哲思结语
""",
        encoding="utf-8",
    )

    insights = parse_insights(rewritten)

    assert len(insights) == 2
    assert insights[0]["title"] == "成本结构的范式转移"
    assert insights[0]["body"] == "传统 SaaS 的边际成本趋近于零。 这不只是财务问题，而是商业模式逻辑的变化。"
    assert insights[1]["title"] == "计量即权力"


def test_parse_insight_strips_sentence_mark_after_bold_title(tmp_path):
    rewritten = tmp_path / "rewritten.md"
    rewritten.write_text(
        """## 3. 核心洞察 (Core Insights)

1. **增长的时间尺度需要重新校准**。不是明天，不是下周，而是三个月。

## 4. 哲思结语
""",
        encoding="utf-8",
    )

    insights = parse_insights(rewritten)

    assert insights[0]["title"] == "增长的时间尺度需要重新校准"
    assert insights[0]["body"] == "不是明天，不是下周，而是三个月。"


def test_parse_philosophical_epilogue_from_rewritten_file():
    path = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学/rewritten.md")

    assert parse_philosophical_epilogue(path) == {}


def test_parse_philosophical_epilogue_with_style_and_quote(tmp_path):
    path = tmp_path / "rewritten.md"
    path.write_text(
        """## 4. 哲思结语 (Philosophical Epilogue)

*William James style*

> 知识不会自动变成力量。它需要一个人在方向未明时押上自己的时间。

## 5. 推荐书单
""",
        encoding="utf-8",
    )

    epilogue = parse_philosophical_epilogue(path)

    assert epilogue["style"] == "William James style"
    assert epilogue["body"] == "知识不会自动变成力量。它需要一个人在方向未明时押上自己的时间。"
    assert epilogue["title"] == "它需要一个人在方向未明时押上自己的时间"
