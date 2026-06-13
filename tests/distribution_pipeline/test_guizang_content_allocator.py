from distribution_pipeline.renderers.guizang.content_allocator import (
    assign_copy_slots,
    build_copy_slots,
    visible_text_nodes,
)


def test_build_copy_slots_removes_title_and_sentence_duplicates():
    slots = build_copy_slots(
        {
            "title": "成本结构的范式转移",
            "body": "成本结构的范式转移。AI 时代的成本随用量线性增长。这会重写商业模式。",
            "reader_takeaway": "AI 时代的成本随用量线性增长。",
        }
    )

    assert slots["hero"] == "成本结构的范式转移"
    assert slots["lead"] == "AI 时代的成本随用量线性增长。"
    assert slots["details"] == ["这会重写商业模式。"]
    assert slots["caption"] == ""


def test_assign_copy_slots_preserves_page_and_adds_slots():
    page = {"title": "Token 是新形态的大宗商品", "body": "判断正在被验证。商业模式会重演。"}

    enriched = assign_copy_slots(page)

    assert enriched is not page
    assert enriched["title"] == page["title"]
    assert enriched["copy_slots"]["sentences"] == ["判断正在被验证。", "商业模式会重演。"]


def test_visible_text_nodes_unescapes_html_entities():
    nodes = visible_text_nodes("<section><p>Token &amp; AI</p><style>.x{}</style></section>")

    assert nodes == ["Token & AI"]
