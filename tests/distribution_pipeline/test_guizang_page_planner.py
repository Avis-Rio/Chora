from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.guizang.page_planner import build_xhs_pages, content_profile


def test_build_xhs_pages_uses_cover_insights_and_closing(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    pages = build_xhs_pages(package, max_cards=6, mode="editorial")

    assert pages[0]["id"] == "xhs-01"
    assert pages[0]["role"] == "cover"
    assert pages[-1]["role"] == "closing"
    assert len(pages) <= 6
    assert all(page["recipe"].startswith("M") for page in pages)


def test_build_xhs_pages_avoids_consecutive_recipe_repetition(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    pages = build_xhs_pages(package, max_cards=6, mode="editorial")
    recipes = [page["recipe"] for page in pages]

    assert all(left != right for left, right in zip(recipes, recipes[1:]))


def test_build_xhs_pages_supports_swiss_recipe_family(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")

    pages = build_xhs_pages(package, max_cards=5, mode="swiss")

    assert all(page["recipe"].startswith("S") for page in pages)
    assert all("copy_slots" in page for page in pages)
    assert pages[1]["copy_slots"]["hero"] == pages[1]["title"]


def test_build_xhs_pages_swiss_routes_specific_recipe_signals():
    package = {
        "source": {"title": "职场系统复盘", "channel": "Chora"},
        "insights": [
            {
                "index": 1,
                "title": "增长不是等待算法，而是主动验证。",
                "body": "旧路径依赖平台分发。新路径先用真实社交验证内容。",
            },
            {
                "index": 2,
                "title": "最大的风险是错误指标。",
                "body": "风险来自把播放量当成信任，把曝光当成复利。",
            },
            {
                "index": 3,
                "title": "系统流程决定复利。",
                "body": "输入、处理、发布、复盘构成完整工作流。",
            },
            {
                "index": 4,
                "title": "行动清单需要可重复。",
                "body": "第一步记录问题。第二步发布观察。第三步主动反馈。第四步复盘表达。",
            },
            {
                "index": 5,
                "title": "TOP 信号来自文本密度。",
                "body": "排名不是装饰，而是让读者先看最强证据。",
            },
            {
                "index": 6,
                "title": "四个能力共同构成系统。",
                "body": "记录问题。发布观察。主动反馈。复盘表达。",
            },
        ],
        "philosophical_epilogue": {},
        "image_assets": {
            "selected_assets": [
                {
                    "asset_id": "xhs-07-hero",
                    "status": "available",
                    "render_path": "assets/images/xhs-07-hero.jpg",
                    "target_insight_index": 6,
                    "target_pages": ["xhs-07"],
                    "subject_map": {
                        "focus": "center visual",
                        "safe_zone": "upper-left text block",
                        "quiet_zone": "left band",
                        "light": "restrained",
                    },
                }
            ]
        },
    }

    pages = build_xhs_pages(package, mode="swiss")
    recipes_by_insight = {
        page.get("insight_index"): page["recipe"] for page in pages if page["role"] == "insight"
    }

    assert recipes_by_insight[1] == "S02"
    assert recipes_by_insight[2] == "S05"
    assert recipes_by_insight[3] == "S06"
    assert recipes_by_insight[4] == "S11"
    assert recipes_by_insight[5] == "S10"
    assert recipes_by_insight[6] == "S08"


def test_build_xhs_pages_swiss_does_not_force_image_recipe_without_subject_map():
    package = {
        "source": {"title": "产品复盘", "channel": "Chora"},
        "insights": [
            {
                "index": 1,
                "title": "图像不能自动变成封面。",
                "body": "没有 subject map，标题不能直接压在图片上。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {
            "selected_assets": [
                {
                    "asset_id": "unsafe-hero",
                    "status": "available",
                    "render_path": "assets/images/unsafe.jpg",
                    "target_pages": ["xhs-02"],
                    "target_insight_index": 1,
                }
            ]
        },
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[1]["image"]["src"] == "assets/images/unsafe.jpg"
    assert pages[1]["recipe"] == "S05"
    assert pages[1]["recipe"] != "S04"
    assert pages[1]["recipe"] != "S08"


def test_build_xhs_pages_resolves_relative_image_path_for_subject_map(tmp_path, monkeypatch):
    xhs_dir = tmp_path / "package" / "xhs"
    images_dir = xhs_dir / "assets" / "images"
    images_dir.mkdir(parents=True)
    image_path = images_dir / "evidence.jpg"
    image_path.write_bytes(b"fake-image")
    captured = {}

    def fake_build_subject_map(image, page, image_path=None, cache_dir=None):
        captured["image_path"] = image_path
        captured["cache_dir"] = cache_dir
        return {
            "type": "landscape",
            "auto_generated": False,
            "focus": "center",
            "safe_zone": "upper-left text block",
        }

    monkeypatch.setattr(
        "distribution_pipeline.renderers.guizang.page_planner.build_subject_map",
        fake_build_subject_map,
    )
    package = {
        "source": {"title": "产品复盘", "channel": "Chora"},
        "insights": [
            {
                "index": 1,
                "title": "图像可以进入 vision。",
                "body": "相对路径也应该解析为真实本地文件。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {
            "_render_root": str(xhs_dir),
            "selected_assets": [
                {
                    "asset_id": "evidence",
                    "status": "available",
                    "render_path": "assets/images/evidence.jpg",
                    "target_pages": ["xhs-02"],
                    "target_insight_index": 1,
                }
            ],
        },
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[1]["image"]["subject_map"]["type"] == "landscape"
    assert captured["image_path"] == image_path
    assert captured["cache_dir"] == images_dir


def test_build_xhs_pages_turns_long_cover_title_into_growth_hook(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")
    package["source"][
        "title"
    ] = "谷歌AI的14年、Gemini翻身之战，与视觉理解模型：专访DeepMind前核心科学家Andrew"

    pages = build_xhs_pages(package, max_cards=6, mode="editorial")

    assert pages[0]["title_lines"] == ["谷歌 AI 慢了半拍", "但还没输"]
    assert "先看几个反直觉判断" in pages[0]["body"]


def test_build_xhs_pages_uses_evidence_recipe_when_image_is_available(tmp_path):
    content = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    package = build_content_package(content, tmp_path / "pkg")
    package["image_assets"]["selected_assets"] = [
        {
            "asset_id": "xhs-02-evidence",
            "status": "available",
            "render_path": "assets/images/xhs-02-evidence.png",
            "target_pages": ["xhs-02"],
            "caption": "AI research lab",
            "provider": "pexels",
        }
    ]

    pages = build_xhs_pages(package, max_cards=6, mode="editorial")

    assert pages[1]["id"] == "xhs-02"
    assert pages[1]["recipe"] == "M10"
    assert pages[1]["image"]["src"] == "assets/images/xhs-02-evidence.png"


def test_build_xhs_pages_matches_evidence_by_insight_index_over_old_page_id():
    package = {
        "source": {"title": "How To Grow An Audience If You Have 0 Followers", "channel": "Dan Koe"},
        "insights": [
            {"index": index, "title": f"洞察{index}", "body": f"解释{index}。"} for index in range(1, 9)
        ],
        "philosophical_epilogue": {"title": "哲思结语", "body": "行动现在发生。"},
        "image_assets": {
            "selected_assets": [
                {
                    "asset_id": "old-xhs-07-evidence",
                    "status": "available",
                    "render_path": "assets/images/old-xhs-07.png",
                    "target_pages": ["xhs-07"],
                    "target_insight_index": 6,
                    "caption": "wrong skipped insight",
                },
                {
                    "asset_id": "insight-7-evidence",
                    "status": "available",
                    "render_path": "assets/images/insight-7.png",
                    "target_pages": ["xhs-05"],
                    "target_insight_index": 7,
                    "caption": "right selected insight",
                },
            ]
        },
    }

    pages = build_xhs_pages(package, mode="editorial")
    page_for_insight_7 = next(page for page in pages if page.get("insight_index") == 7)

    assert page_for_insight_7["id"] == "xhs-07"
    assert page_for_insight_7["image"]["src"] == "assets/images/insight-7.png"
    assert all((page.get("image") or {}).get("src") != "assets/images/old-xhs-07.png" for page in pages)


def test_build_xhs_pages_auto_uses_growth_depth_deck_and_keeps_philosophy():
    package = {
        "source": {"title": "谷歌AI的14年", "channel": "硅谷101"},
        "insights": [
            {"index": index, "title": f"洞察{index}", "body": f"完整解释{index}。"} for index in range(1, 11)
        ],
        "philosophical_epilogue": {
            "title": "时间不可逆",
            "body": "知识不会自动变成力量。时间是唯一不可逆的资源。",
            "style": "William James style",
        },
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert len(pages) == 10
    assert [page["insight_index"] for page in pages if page["role"] == "insight"] == [1, 2, 3, 5, 7, 8, 10]
    assert pages[0]["title_lines"] == ["谷歌 AI 慢了半拍", "但还没输"]
    assert [page["kicker"] for page in pages if page["role"] == "insight"][:2] == ["Insight 01", "Insight 02"]
    assert pages[-2]["role"] == "philosophy"
    assert pages[-2]["body"] == "知识不会自动变成力量。时间是唯一不可逆的资源。"
    assert pages[-1]["role"] == "closing"
    assert pages[-1]["title"] == "读完整篇前，先带走这三点"
    assert len(pages[-1]["items"]) == 3


def test_build_xhs_pages_routes_short_insights_to_atmospheric_recipe():
    package = {
        "source": {"title": "谷歌AI的14年", "channel": "硅谷101"},
        "insights": [
            {"index": 1, "title": "研究品位的本质是时间管理。", "body": "判断比执行更重要。"},
            {"index": 2, "title": "数据是护城河。", "body": "筛选方法决定模型上限。"},
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["recipe"] == "M09"
    assert pages[2]["recipe"] != "M09"


def test_build_xhs_pages_routes_medium_single_sentence_to_marginalia_recipe():
    package = {
        "source": {"title": "Neo Lab", "channel": "硅谷101"},
        "insights": [
            {
                "index": 1,
                "title": "Neo Lab的窗口期是有限的。",
                "body": "开源模型成熟、融资环境宽松、大公司注意力集中在编程，这三个条件同时成立的时间窗口可能只有两年左右。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["recipe"] == "M11"


def test_build_xhs_pages_routes_short_two_sentence_body_to_marginalia_recipe():
    package = {
        "source": {"title": "创作者增长", "channel": "Dan Koe"},
        "insights": [
            {
                "index": 1,
                "title": "增长的时间尺度需要重新校准。",
                "body": "不是明天，不是下周，而是两周、四周、三个月。对时间尺度的错误预期，是大多数人放弃的真正原因。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["recipe"] == "M11"


def test_build_xhs_pages_keeps_solitude_sparse_insight_out_of_empty_essay():
    package = {
        "source": {"title": "Why People Disappear | The Psychology of Being Alone", "channel": "Aperture"},
        "insights": [
            {"index": 1, "title": "孤独的历史性转变", "body": "孤独曾是一种主动选择。"},
            {"index": 2, "title": "回避的神经机制", "body": "回避会被大脑强化。"},
            {
                "index": 3,
                "title": "第三空间的政治经济学",
                "body": "没有第三空间，成年人的偶遇和无目的连接就失去了物理基础。",
            },
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")
    third_space_page = next(page for page in pages if page.get("insight_index") == 3)

    assert third_space_page["recipe"] != "M03"


def test_build_xhs_pages_keeps_repeated_sparse_insights_out_of_empty_essay():
    package = {
        "source": {"title": "一篇关于注意力的文章", "channel": "Chora"},
        "insights": [
            {"index": 1, "title": "注意力不是意志力。", "body": "环境先决定选择。"},
            {"index": 2, "title": "复杂系统需要慢变量。", "body": "真正改变结果的，往往不是即时反馈。"},
            {"index": 3, "title": "行动必须留下痕迹。", "body": "没有记录，经验很快消失。"},
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")
    insight_recipes = [page["recipe"] for page in pages if page["role"] == "insight"]

    assert "M03" not in insight_recipes


def test_build_xhs_pages_routes_title_comparison_to_before_after_recipe():
    package = {
        "source": {"title": "创作者增长", "channel": "Dan Koe"},
        "insights": [
            {
                "index": 1,
                "title": "增长不是等待算法，而是主动验证。",
                "body": "旧路径依赖平台分发。新路径先用真实社交验证内容。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["recipe"] == "M15"


def test_build_xhs_pages_routes_checklist_signal_to_checklist_recipe():
    package = {
        "source": {"title": "创作者增长", "channel": "Dan Koe"},
        "insights": [
            {
                "index": 1,
                "title": "两种习惯构成增长方法。",
                "body": "第一步，记录问题。第二步，发布观察。第三步，主动找人反馈。第四步，复盘下一次表达。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["recipe"] == "M05"


def test_build_xhs_pages_uses_category_cookbook_for_travel_photo_note():
    package = {
        "source": {"title": "云南旅行三天两夜", "channel": "Chora", "tags": ["旅行"]},
        "insights": [
            {
                "index": 1,
                "title": "路线要先服务体力，而不是景点数量。",
                "body": "第一天只走古城和咖啡馆，把高海拔徒步留给第二天。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {
            "selected_assets": [
                {
                    "asset_id": "travel-field-note",
                    "status": "available",
                    "render_path": "assets/images/travel.jpg",
                    "target_pages": ["xhs-02"],
                    "target_insight_index": 1,
                    "caption": "云南古城街道",
                }
            ]
        },
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["rednote_category"]["key"] == "travel"
    assert pages[1]["recipe"] == "M02"


def test_build_xhs_pages_uses_category_sequence_without_forcing_photo_recipe():
    package = {
        "source": {"title": "云南旅行路线复盘", "channel": "Chora", "tags": ["旅行"]},
        "insights": [
            {
                "index": 1,
                "title": "路线要先服务体力。",
                "body": "第一天压缩景点，第二天再安排徒步路径。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["rednote_category"]["key"] == "travel"
    assert pages[1]["recipe"] != "M02"
    assert pages[1]["recipe"] == "M14"


def test_build_xhs_pages_records_overlay_and_thumbnail_qa_flags():
    package = {
        "source": {"title": "旅行封面", "channel": "Chora", "tags": ["旅行"]},
        "insights": [{"index": 1, "title": "现场比攻略重要。", "body": "照片只承载证据，不替代判断。"}],
        "philosophical_epilogue": {},
        "image_assets": {
            "selected_assets": [
                {
                    "asset_id": "cover-hero",
                    "status": "available",
                    "render_path": "assets/images/cover.jpg",
                    "target_pages": ["xhs-01"],
                    "subject_map": {
                        "focus": "mountain in center",
                        "safe_zone": "lower-left",
                        "quiet_zone": "fog band",
                        "light": "restrained",
                    },
                }
            ]
        },
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[0]["recipe"] == "M16"
    assert "text_on_image_requires_subject_map" in pages[0]["qa_flags"]
    assert "thumbnail_check_required" in pages[0]["qa_flags"]


def test_content_profile_detects_creator_growth():
    source = {"title": "How To Grow An Audience If You Have 0 Followers", "channel": "Dan Koe"}
    insights = [{"title": "互惠原则是社交增长的底层机制", "body": "关系网络是手动杠杆。"}]

    assert content_profile(source, insights) == "creator-growth"


def test_build_xhs_pages_swiss_extracts_metric_tokens_for_data_visuals():
    package = {
        "source": {"title": "职场指标复盘", "channel": "Chora", "tags": ["职场"]},
        "insights": [
            {
                "index": 1,
                "title": "成本下降 20% 才是真指标。",
                "body": "团队用 3 周把返工率从 18% 降到 9%。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[1]["recipe"] == "S09"
    assert pages[1]["metric_tokens"][0]["raw"] == "20%"
    assert pages[1]["stats"][0]["source"] == "extracted"
    assert "uses_extracted_metrics" in pages[1]["qa_flags"]


def test_build_xhs_pages_swiss_routes_single_metric_to_file_card():
    package = {
        "source": {"title": "Token 经济学", "channel": "硅谷101", "tags": ["Technology"]},
        "insights": [
            {
                "index": 1,
                "title": "价格分化创造套利空间",
                "body": "中美模型 50 倍的价差，不只是竞争威胁，更是商业机会。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[1]["metric_tokens"][0]["raw"] == "50 倍"
    assert pages[1]["recipe"] == "S03"
    assert pages[1]["recipe"] != "S09"


def test_build_xhs_pages_swiss_avoids_kpi_tower_without_real_metric_tokens():
    package = {
        "source": {"title": "Token 经济学", "channel": "硅谷101", "tags": ["Technology"]},
        "insights": [
            {
                "index": 1,
                "title": "成本结构的范式转移",
                "body": "传统 SaaS 的边际成本趋近于零，AI 时代的成本随用量线性增长。这是商业模式逻辑的变化。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[1]["metric_tokens"] == []
    assert pages[1]["recipe"] != "S09"
    assert "uses_proxy_metrics" not in pages[1]["qa_flags"]


def test_build_xhs_pages_swiss_pipeline_expands_chinese_enumeration():
    package = {
        "source": {"title": "Token 经济学", "channel": "硅谷101", "tags": ["Technology"]},
        "insights": [
            {
                "index": 1,
                "title": "中国模型出海的结构性优势",
                "body": "低电价、MoE 架构、云厂商垂直整合，三重因素叠加。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[1]["recipe"] == "S06"
    assert [item["title"] for item in pages[1]["items"]] == ["低电价", "MoE 架构", "云厂商垂直整合"]
    assert [item["note"] for item in pages[1]["items"]] == ["成本底座", "效率结构", "供给链路"]


def test_build_xhs_pages_swiss_uses_comparison_recipe_for_strong_vs_weak_models():
    package = {
        "source": {"title": "Token 经济学", "channel": "硅谷101", "tags": ["Technology"]},
        "insights": [
            {
                "index": 1,
                "title": "“越贵越便宜”的悖论",
                "body": "在 agent 场景下，模型的单价不等于任务的综合成本。强模型一次完成，弱模型反复迭代。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[1]["recipe"] == "S02"


def test_content_profile_detects_solitude_psychology():
    source = {"title": "Why People Disappear | The Psychology of Being Alone", "channel": "Aperture"}
    insights = [{"title": "孤独与孤寂的根本区别", "body": "孤独是主动选择。"}]

    assert content_profile(source, insights) == "solitude-psychology"


def test_build_xhs_pages_swiss_closing_stays_takeaway_ledger_after_takeaway_page():
    package = {
        "source": {"title": "Token 经济学", "channel": "硅谷101", "tags": ["Technology"]},
        "insights": [
            {"index": 1, "title": "判断一", "body": "这是一段普通论述。"},
            {"index": 2, "title": "判断二", "body": "这是一段普通论述。"},
            {"index": 3, "title": "判断三", "body": "这是一段普通论述。"},
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[-2]["recipe"] == "S07"
    assert pages[-1]["role"] == "closing"
    assert pages[-1]["recipe"] == "S07"


def test_build_xhs_pages_compresses_growth_title_without_losing_original():
    package = {
        "source": {"title": "谷歌AI的14年", "channel": "硅谷101"},
        "insights": [
            {
                "index": 1,
                "title": "大公司的最大风险不是技术落后，而是优先级漂移。",
                "body": "谷歌拥有几乎所有关键技术的原始版本。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["title"] == "优先级漂移，比技术落后更危险。"
    assert pages[1]["original_title"] == "大公司的最大风险不是技术落后，而是优先级漂移。"


def test_build_xhs_pages_does_not_route_two_sentence_prose_to_pipeline():
    package = {
        "source": {"title": "谷歌AI的14年", "channel": "硅谷101"},
        "insights": [
            {
                "index": 1,
                "title": "硅谷的知识流动是双向的。",
                "body": "谷歌的研究成果通过人才流动传播到OpenAI。OpenAI的技术路线又反过来倒逼谷歌调整方向。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[1]["recipe"] != "M14"


def test_build_xhs_pages_routes_philosophy_to_hero_question():
    package = {
        "source": {"title": "谷歌AI的14年", "channel": "硅谷101"},
        "insights": [{"index": 1, "title": "技术时机", "body": "知识需要行动。"}],
        "philosophical_epilogue": {"title": "时间不可逆", "body": "时间，是唯一不可逆的资源。"},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="editorial")

    assert pages[-2]["role"] == "philosophy"
    assert pages[-2]["recipe"] == "M13"


def test_build_xhs_pages_swiss_routes_geographic_insight_to_map():
    package = {
        "source": {"title": "黄金东移与全球权力转移", "channel": "硅谷101", "tags": ["Economics"]},
        "insights": [
            {
                "index": 1,
                "title": "黄金正在从西方流向东方",
                "body": "中国、印度和中东央行持续增持黄金，而欧美投资者ETF持仓下降。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="swiss")

    assert pages[1]["recipe"] == "S13"
    assert pages[1]["map_route"]["origin"] == "西方"
    assert pages[1]["map_route"]["destination"] == "印度"
    assert "中国" in pages[1]["map_route"]["stops"]


def test_build_xhs_pages_swiss_map_does_not_override_metric_signal():
    package = {
        "source": {"title": "Token 经济学", "channel": "硅谷101", "tags": ["Technology"]},
        "insights": [
            {
                "index": 1,
                "title": "价格分化创造套利空间",
                "body": "中美模型 50 倍的价差，不只是竞争威胁，更是商业机会。",
            }
        ],
        "philosophical_epilogue": {},
        "image_assets": {},
    }

    pages = build_xhs_pages(package, mode="swiss")

    # metric 信号强于 map 信号，应走 S03 而非 S13
    assert pages[1]["recipe"] == "S03"
