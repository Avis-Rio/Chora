from distribution_pipeline.renderers.guizang.title_breaker import semantic_title_lines


def test_semantic_title_lines_avoid_single_character_tail():
    lines = semantic_title_lines("反向萨义德主义（Reverse Saidism）的陷阱", target=9, max_lines=3, min_tail=3)

    assert len(lines) <= 3
    assert all(len(line) >= 3 for line in lines)
    assert not any(line in {"的", "陷", "阱"} for line in lines)
    assert "Reverse Saidism" in "".join(lines)


def test_semantic_title_lines_keep_common_concepts_together():
    lines = semantic_title_lines("沉默作为最后的自主权", target=8, max_lines=3, min_tail=3)

    assert all(len(line) >= 3 for line in lines)
    assert "自主权" in lines[-1]


def test_semantic_title_lines_keep_person_names_together():
    lines = semantic_title_lines("聊聊陀思妥耶夫斯基的作品与人生", target=8, max_lines=2, min_tail=3)

    assert "陀思妥耶夫斯基" in "".join(lines)
    assert not any(line.endswith("陀思妥耶夫斯") for line in lines)
    assert not any(line.startswith("基") for line in lines)


def test_semantic_title_lines_keep_new_form_together():
    lines = semantic_title_lines("Token 是新形态的大宗商品", target=9, max_lines=3, min_tail=3)

    assert "新形态" in "".join(lines)
    assert not any(line.endswith("新形") for line in lines)
    assert not any(line.startswith("态") for line in lines)
    assert not any(line.startswith("的") for line in lines)
