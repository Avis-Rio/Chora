from distribution_pipeline.directors.card_copy import build_card_copies


def _has_common_run(a: str, b: str, n: int = 8) -> bool:
    a = "".join(ch for ch in a if ch.strip())
    b = "".join(ch for ch in b if ch.strip())
    return any(a[i : i + n] in b for i in range(max(0, len(a) - n + 1)))


def test_card_copy_splits_long_argument_into_short_headline_and_subhead():
    copies = build_card_copies(
        {"title": "测试", "channel": "Chora"},
        [
            {
                "index": 3,
                "title": "书籍的价值不仅在内容更在其物质形态中的审美与文化传承",
                "body": "王强谈书时，重点不只是文本，而是书作为物件带来的触感、版本、装帧与时代气息。纸张和边注也保存阅读史。",
            }
        ],
    )

    copy = copies[0]
    assert copy["headline"] == "书籍的价值"
    assert copy["subhead"].startswith("不仅在内容")
    assert len(copy["headline_lines"]) <= 2
    assert all(line[-1] not in "在与和的更不也是于中" for line in copy["headline_lines"])


def test_card_copy_pullquote_does_not_repeat_body_or_subhead():
    copy = build_card_copies(
        {},
        [
            {
                "index": 1,
                "title": "审美经验改变阅读判断",
                "body": "阅读不只是吸收内容，也是在纸张、装帧、气味和版本之间形成经验。收藏让知识变得可触摸。",
            }
        ],
    )[0]

    assert copy["pullquote"]
    assert not _has_common_run(copy["pullquote"], copy["body"])
    assert not _has_common_run(copy["pullquote"], copy["subhead"])


def test_card_copy_keeps_enough_payload_for_dense_cards():
    copy = build_card_copies(
        {},
        [
            {
                "index": 7,
                "title": "文字阅读激发想象力，是创新的情感基础",
                "body": "文字阅读迫使读者在脑海中生成场景、声音与人物关系。它不像视频那样直接给出图像，而是让想象力持续参与。长期阅读训练的是抽象能力、情绪辨识和复杂判断。创新往往来自这种看不见的内在活动。",
            }
        ],
    )[0]

    assert copy["min_payload_ok"] is True
    assert copy["copy_density"] in {"medium", "high"}
    assert len(copy["points"]) >= 2
    assert len(copy["details"]) >= 2
    assert len(copy["body"]) > 80
