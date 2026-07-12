from distribution_pipeline.renderers.xhs_plan import build_xhs_card_plan


def test_build_xhs_card_plan_creates_cover_insights_and_cta():
    source = {"title": "Token经济学：AI时代的新货币战争", "channel": "硅谷101"}
    insights = [
        {"index": 1, "title": "成本结构的范式转移", "body": "AI 产品让推理成为真实成本。"},
        {"index": 2, "title": "计量即权力", "body": "谁定义 Token 的计量方式，谁就定义边界。"},
    ]

    plan = build_xhs_card_plan(source, insights, max_cards=5)

    assert plan[0]["type"] == "cover-poster"
    assert plan[-1]["type"] == "closing-card"
    assert any(card["type"] == "single-insight" for card in plan)
    assert len(plan) <= 5


def test_build_xhs_card_plan_auto_uses_all_insights_and_epilogue():
    source = {"title": "谷歌AI的14年", "channel": "硅谷101"}
    insights = [
        {"index": index, "title": f"洞察{index}", "body": f"完整解释{index}。"} for index in range(1, 11)
    ]
    epilogue = {"title": "时间不可逆", "body": "知识不会自动变成力量。时间是唯一不可逆的资源。"}

    plan = build_xhs_card_plan(source, insights, epilogue=epilogue)

    assert len(plan) == 13
    assert [card["insight_index"] for card in plan if card["type"] == "single-insight"] == list(range(1, 11))
    assert plan[-2]["type"] == "philosophical-card"
    assert plan[-1]["type"] == "closing-card"


def test_build_xhs_card_plan_growth_depth_compresses_without_losing_body_route():
    source = {"title": "谷歌AI的14年、Gemini翻身之战", "channel": "硅谷101"}
    insights = [
        {"index": index, "title": f"洞察{index}", "body": f"完整解释{index}。"} for index in range(1, 11)
    ]
    epilogue = {"title": "时间不可逆", "body": "知识不会自动变成力量。"}

    plan = build_xhs_card_plan(source, insights, epilogue=epilogue, strategy="growth-depth")

    assert len(plan) == 10
    assert plan[0]["title_lines"] == ["谷歌 AI 慢了半拍", "但还没输"]
    assert [card["insight_index"] for card in plan if card["type"] == "single-insight"] == [
        1,
        2,
        3,
        5,
        7,
        8,
        10,
    ]
    assert plan[-2]["type"] == "philosophical-card"
    assert plan[-1]["items"][0]["title"] == "洞察1"
    assert "3 个延伸洞察" in plan[-1]["body"]


def test_build_xhs_card_plan_growth_depth_uses_audience_hook():
    source = {
        "title": "How To Grow An Audience If You Have 0 Followers (It's Only 2 Habits)",
        "channel": "Dan Koe",
    }
    insights = [
        {"index": 1, "title": "失败是跨领域技能的隐性积累", "body": "失败建立模式库。"},
        {"index": 2, "title": "算法是放大器，不是发动机", "body": "增长需要手动杠杆。"},
    ]

    plan = build_xhs_card_plan(source, insights, strategy="growth-depth")

    assert plan[0]["title_lines"] == ["从零粉丝开始", "增长靠的不是算法"]
    assert "0 粉丝" not in plan[0]["title"]
    assert "验证内容，真实社交" in plan[0]["body"]


def test_build_xhs_card_plan_growth_depth_uses_solitude_hook():
    source = {"title": "Why People Disappear | The Psychology of Being Alone", "channel": "Aperture"}
    insights = [
        {"index": 1, "title": "孤独的历史性转变", "body": "孤独不只是个人选择。"},
        {"index": 2, "title": "回避的神经机制", "body": "回避会被大脑强化。"},
    ]

    plan = build_xhs_card_plan(source, insights, strategy="growth-depth")

    assert plan[0]["title_lines"] == ["为什么越来越多人", "选择消失"]
    assert "现代生活正在让连接变得更难" in plan[0]["body"]
