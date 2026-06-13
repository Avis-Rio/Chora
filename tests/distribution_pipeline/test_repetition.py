from distribution_pipeline.reviewers.repetition import review_repetition


def test_review_repetition_flags_duplicate_metaphors():
    briefs = [
        {"visual_metaphor": "账本", "composition": {"text_position": "center"}},
        {"visual_metaphor": "账本", "composition": {"text_position": "center"}},
    ]

    result = review_repetition(briefs)

    assert not result["passed"]
    assert "duplicate_visual_metaphor" in result["issues"]
    assert "duplicate_composition" in result["issues"]
