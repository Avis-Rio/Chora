import re

from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_xhs_package


def test_guizang_xhs_html_has_at_most_one_quote_block_per_card(tmp_path):
    package = {
        "source": {"title": "测试文章", "channel": "Chora", "tags": []},
        "insights": [
            {
                "index": 1,
                "title": "书籍的价值不仅在内容更在其物质形态中的审美与文化传承",
                "body": "王强谈书时，重点不只是文本，而是书作为物件带来的触感、版本、装帧与时代气息。",
            }
        ],
        "card_copy": [
            {
                "insight_index": 1,
                "headline": "书籍的价值",
                "headline_lines": ["书籍的价值"],
                "subhead": "不仅在内容，也在纸张与装帧之中。",
                "body": "王强谈书时，重点不只是文本，而是书作为物件带来的触感、版本、装帧与时代气息。",
                "pullquote": "一本书也是一种被保存下来的时间。",
                "layout_intent": "object-culture",
                "recipe_hint": "M02",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    render_guizang_xhs_package(package, tmp_path, max_cards=3, mode="editorial")
    html = (tmp_path / "xhs" / "index.html").read_text(encoding="utf-8")
    for section in re.findall(r'<section class="poster xhs".*?</section>', html, flags=re.S):
        quote_count = len(re.findall(r'class="(?:callout|takeaway-band)"', section))
        assert quote_count <= 1
    assert "书籍的价值" in html
    assert "不仅在内容" in html
    assert "一本书也是一种被保存下来的时间" in html
    assert "takeaway-band" not in html
