from distribution_pipeline.renderers.xhs_copy import build_xhs_caption, build_xhs_publish_md, build_xhs_tags


def test_build_xhs_publish_md_has_copyable_caption_tags_and_comment():
    source = {
        "title": "Token经济学：AI时代的新货币战争",
        "channel": "硅谷101",
        "tags": ["Technology", "Economics", "Power & Politics"],
    }
    insights = [
        {"title": "成本不是价格，而是权力边界。", "body": "Token 决定谁能调用智能。"},
        {"title": "模型竞争会变成分配竞争。", "body": "算力、数据和产品都会被重新排序。"},
    ]

    markdown = build_xhs_publish_md(source, insights, brand={"chora_url": "https://example.com"})

    assert "## 小红书正文｜复制此段" in markdown
    assert "## Tags｜复制此段" in markdown
    assert "## 首评｜可选" in markdown
    assert "```text" in markdown
    assert "#科技" in markdown
    assert "#商业思考" in markdown
    assert "#Chora" in markdown
    assert "https://example.com" in markdown


def test_build_xhs_publish_md_keeps_source_title_after_insight_backup():
    source = {
        "title": "Token经济学：AI时代的新货币战争",
        "channel": "硅谷101",
        "tags": ["Technology"],
    }
    insights = [
        {"title": "成本结构的范式转移", "body": "成本随用量线性增长。"},
        {"title": "Token 效率是下一个主战场", "body": "减少无效 token。"},
    ]

    markdown = build_xhs_publish_md(source, insights)

    assert markdown.splitlines()[0] == "# Token经济学：AI时代的新货币战争"
    assert "2. Token 效率是下一个主战场：减少无效 token。" in markdown


def test_build_xhs_tags_dedupes_and_adds_semantic_tags():
    source = {"title": "How To Grow An Audience If You Have 0 Followers", "tags": ["AI", "AI"]}
    insights = [{"title": "创作者增长靠真实社交", "body": "粉丝不是数字，而是关系网络。"}]

    tags = build_xhs_tags(source, insights)

    assert tags.count("人工智能") == 1
    assert "创作者成长" in tags
    assert "内容创作" in tags
    assert "Rhizomata" in tags


def test_build_xhs_tags_keeps_brand_tags_when_semantic_tags_are_many():
    source = {
        "title": "Token经济学：AI时代的新货币战争",
        "channel": "硅谷101",
        "tags": ["Technology", "Economics", "Power & Politics"],
    }
    insights = [
        {"title": "推理成本会重塑商业模式", "body": "算力、token 和价格会一起改变产品边界。"},
    ]

    tags = build_xhs_tags(source, insights)

    assert "AI商业化" in tags
    assert "AI成本" in tags
    assert "Chora" in tags
    assert "Rhizomata" in tags
    assert len(tags) <= 12


def test_build_xhs_caption_keeps_all_core_insight_titles():
    source = {"title": "长文章", "channel": "Chora"}
    insights = [{"title": f"洞察{index}", "body": f"正文{index}。"} for index in range(1, 7)]

    caption = build_xhs_caption(source, insights)

    assert "洞察1" in caption
    assert "洞察5" in caption
    assert "洞察6" not in caption


def test_build_xhs_caption_uses_topic_specific_angle_instead_of_generic_template():
    source = {"title": "Token经济学：AI时代的新货币战争", "channel": "硅谷101", "tags": ["Technology"]}
    insights = [{"title": "成本不是价格，而是权力边界。", "body": "Token 决定谁能调用智能。"}]

    caption = build_xhs_caption(source, insights)

    assert "成本结构" in caption
    assert "AI 商业化" in caption
    assert "这组卡片整理自 Chora 的深度改写文章" not in caption
    assert "如果只记一件事" not in caption
