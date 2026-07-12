from distribution_pipeline.renderers.guizang.title_budget import title_variants


def test_title_variants_create_display_title_under_recipe_budget():
    variants = title_variants("学术大师的严谨与谦逊形塑了知识的纯粹也赋予学问以生命的温度", "M03")

    assert len(variants["display_title"]) <= variants["title_budget"]["max_chars"]
    assert len(variants["title_lines"]) <= variants["title_budget"]["max_lines"]
    assert all(len(line) <= variants["title_budget"]["line_chars"] + 2 for line in variants["title_lines"])


def test_title_variants_keep_short_title_compact():
    variants = title_variants("阅读收藏与翻译之间形成一种私人知识谱系", "S12")

    assert 4 <= len(variants["short_title"]) <= 10
    assert len(variants["display_title"]) <= 16
