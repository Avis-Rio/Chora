from distribution_pipeline.reviewers.text_density import review_text_density


def test_review_text_density_flags_overlong_title():
    card = {
        "title": "这是一个明显过长并且不适合出现在卡片主标题区域里的标题",
        "body": "短正文",
    }

    result = review_text_density(card, max_title_chars=18, max_body_chars=120)

    assert not result["passed"]
    assert "title_too_long" in result["issues"]
