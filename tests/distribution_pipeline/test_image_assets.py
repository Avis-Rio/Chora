from pathlib import Path

from distribution_pipeline.assets.image_assets import (
    build_image_asset_plan,
    enrich_image_candidates,
    materialize_image_assets,
)


def _png_bytes(width: int = 800, height: int = 600) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + width.to_bytes(4, "big") + height.to_bytes(4, "big")


def test_build_image_asset_plan_creates_local_cover_and_web_requests():
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    source = {
        "title": "Token经济学：AI时代的新货币战争",
        "tags": ["Technology", "Economics"],
    }
    insights = [{"index": 1, "title": "Token 是新的成本账本", "one_liner": "AI 成本被重新计量"}]
    visual_briefs = [
        {
            "insight_index": 1,
            "composition": {"focal_point": "账本"},
            "visual_metaphor": "账本作为成本隐喻",
        }
    ]
    visual_system = {"visual_motifs": ["账本", "仪表盘"]}

    plan = build_image_asset_plan(source, insights, visual_briefs, visual_system, content_dir)

    assert plan["local_assets"][0]["asset_id"] == "source-cover"
    assert plan["local_assets"][0]["target_pages"] == ["xhs-01"]
    assert plan["requests"][0]["query"] == "AI compute data center"
    assert plan["requests"][0]["search_urls"]["pexels"].startswith("https://www.pexels.com/search/")
    assert "unsplash" in plan["requests"][0]["search_urls"]
    assert "wallhaven" in plan["requests"][0]["search_urls"]
    assert plan["requests"][1]["target_insight_index"] == 1


def test_build_image_asset_plan_uses_short_semantic_queries():
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    plan = build_image_asset_plan(
        {"title": "一次组织合并后的优先级漂移", "tags": []},
        [{"index": 1, "title": "数据是大模型竞争中最不透明的差异点", "one_liner": "数据筛选是护城河"}],
        [],
        {"visual_motifs": []},
        content_dir,
    )

    assert plan["requests"][0]["query"] == "research team strategy meeting"
    assert plan["requests"][1]["query"] == "data center machine learning"


def test_build_image_asset_plan_uses_creator_growth_queries():
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    insights = [
        {"index": index, "title": f"洞察{index}", "one_liner": "先用真实社交验证内容。"}
        for index in range(1, 8)
    ]
    insights[0] = {"index": 1, "title": "算法是放大器，不是发动机", "one_liner": "先验证内容，再谈平台。"}
    insights[4] = {"index": 5, "title": "互惠原则是社交增长的底层机制", "one_liner": "持续给予价值会自然激活回馈。"}
    insights[6] = {"index": 7, "title": "初学者有一个被忽视的优势", "one_liner": "选择更少，专注更强。"}

    plan = build_image_asset_plan(
        {"title": "How To Grow An Audience If You Have 0 Followers", "tags": []},
        insights,
        [],
        {"visual_motifs": []},
        content_dir,
    )

    assert plan["requests"][0]["query"] == "social media content creator"
    assert plan["requests"][1]["query"] == "social media analytics dashboard"
    assert plan["requests"][2]["query"] == "creative networking coffee meeting"
    assert plan["requests"][3]["query"] == "focused creator desk"


def test_build_image_asset_plan_uses_solitude_psychology_queries():
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    insights = [
        {"index": index, "title": f"洞察{index}", "one_liner": "独处不等于失败。"}
        for index in range(1, 8)
    ]
    insights[0] = {"index": 1, "title": "孤独的历史性转变", "one_liner": "孤独曾是被尊重的主动选择。"}
    insights[4] = {"index": 5, "title": "外在动机对身份的侵蚀", "one_liner": "社交媒体把分享变成表演。"}
    insights[6] = {"index": 7, "title": "孤独与孤寂的根本区别", "one_liner": "孤独是主动选择，孤寂是连接痛苦。"}

    plan = build_image_asset_plan(
        {"title": "Why People Disappear | The Psychology of Being Alone", "tags": ["Psychology"]},
        insights,
        [],
        {"visual_motifs": []},
        content_dir,
    )

    assert plan["requests"][0]["query"] == "person alone by window"
    assert plan["requests"][1]["query"] == "person writing alone window"
    assert plan["requests"][2]["query"] == "person mirror smartphone social media"
    assert plan["requests"][3]["query"] == "solitary person open landscape"


def test_build_image_asset_plan_prioritizes_third_space_visual():
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    insights = [
        {"index": index, "title": f"洞察{index}", "one_liner": "独处不等于失败。"}
        for index in range(1, 8)
    ]
    insights[0] = {"index": 1, "title": "孤独的历史性转变", "one_liner": "孤独曾是被尊重的主动选择。"}
    insights[2] = {"index": 3, "title": "第三空间的政治经济学", "one_liner": "公共空间消失后，偶遇失去物理基础。"}
    insights[4] = {"index": 5, "title": "外在动机对身份的侵蚀", "one_liner": "社交媒体把分享变成表演。"}

    plan = build_image_asset_plan(
        {"title": "Why People Disappear | The Psychology of Being Alone", "tags": ["Psychology"]},
        insights,
        [],
        {"visual_motifs": []},
        content_dir,
    )

    evidence_insights = [
        request["target_insight_index"]
        for request in plan["requests"]
        if request["role"] == "evidence"
    ]
    evidence_queries = [
        request["query"]
        for request in plan["requests"]
        if request["role"] == "evidence"
    ]

    assert evidence_insights[:3] == [1, 3, 5]
    assert "quiet city cafe library" in evidence_queries


def test_build_image_asset_plan_spaces_evidence_requests_across_long_deck():
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    insights = [
        {"index": index, "title": f"洞察{index}", "one_liner": "数据筛选是护城河"}
        for index in range(1, 11)
    ]

    plan = build_image_asset_plan(
        {"title": "谷歌AI的14年", "tags": []},
        insights,
        [],
        {"visual_motifs": []},
        content_dir,
    )

    evidence_targets = [
        request["target_pages"][0]
        for request in plan["requests"]
        if request["role"] == "evidence"
    ]
    evidence_insights = [
        request["target_insight_index"]
        for request in plan["requests"]
        if request["role"] == "evidence"
    ]

    assert evidence_targets == ["xhs-02", "xhs-06", "xhs-08", "xhs-10"]
    assert evidence_insights == [1, 5, 7, 9]


def test_materialize_image_assets_copies_local_cover_and_writes_sources(tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "cover.png").write_bytes(_png_bytes())
    plan = build_image_asset_plan(
        {"title": "Token经济学", "tags": []},
        [],
        [],
        {"visual_motifs": []},
        content_dir,
    )

    materialized = materialize_image_assets(plan, tmp_path / "assets")

    assert materialized["local_assets"][0]["render_path"] == "assets/images/source-cover.png"
    assert materialized["local_assets"][0]["width"] == 800
    assert (tmp_path / "assets" / "images" / "source-cover.png").exists()
    sources = (tmp_path / "assets" / "SOURCES.md").read_text(encoding="utf-8")
    assert "Pexels" not in sources
    assert "pexels:" in sources
    assert "版权状态" in sources


def test_materialize_image_assets_rejects_invalid_local_cover(tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    (content_dir / "cover.jpg").write_bytes(b"\n")
    plan = build_image_asset_plan(
        {"title": "Token经济学", "tags": []},
        [],
        [],
        {"visual_motifs": []},
        content_dir,
    )

    materialized = materialize_image_assets(plan, tmp_path / "assets")

    assert materialized["local_assets"][0]["status"] == "rejected"
    assert materialized["local_assets"][0]["reason"] == "invalid local image bytes"
    assert not (tmp_path / "assets" / "images" / "source-cover.jpg").exists()


def test_enrich_image_candidates_uses_manual_candidates_without_network():
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [],
        "requests": [
            {
                "asset_id": "xhs-02-evidence",
                "role": "evidence",
                "target_pages": ["xhs-02"],
                "query": "AI research lab",
                "candidates": [
                    {
                        "provider": "pexels",
                        "image_url": "https://images.example/lab.png",
                        "source_url": "https://pexels.example/photo/lab",
                        "author": "Ada",
                    }
                ],
            }
        ],
    }

    enriched = enrich_image_candidates(plan)

    request = enriched["requests"][0]
    assert request["status"] == "candidates"
    assert request["candidates"][0]["candidate_id"] == "xhs-02-evidence-pexels-01"
    assert request["candidates"][0]["author"] == "Ada"


def test_enrich_image_candidates_continues_after_provider_error(monkeypatch):
    monkeypatch.setenv("PEXELS_API_KEY", "pexels-test-key")
    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "unsplash-test-key")
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [],
        "requests": [
            {
                "asset_id": "xhs-02-evidence",
                "role": "evidence",
                "target_pages": ["xhs-02"],
                "query": "AI research lab",
            }
        ],
    }

    def fake_fetch_json(url, headers=None):
        if "pexels.com" in url:
            raise RuntimeError("pexels unavailable")
        if "unsplash.com" in url:
            return {
                "results": [
                    {
                        "width": 1200,
                        "height": 800,
                        "alt_description": "Research lab",
                        "urls": {"regular": "https://images.example/unsplash-lab.jpg"},
                        "links": {"html": "https://unsplash.example/photo/lab"},
                        "user": {"name": "Grace", "links": {"html": "https://unsplash.example/grace"}},
                    }
                ]
            }
        return {}

    enriched = enrich_image_candidates(
        plan,
        fetch_json=fake_fetch_json,
        max_candidates=3,
    )

    request = enriched["requests"][0]
    assert request["status"] == "candidates"
    assert request["candidate_errors"] == [{"provider": "pexels", "error": "pexels unavailable"}]
    assert request["candidates"][0]["provider"] == "unsplash"


def test_materialize_image_assets_downloads_selected_web_candidate(tmp_path):
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [],
        "requests": [
            {
                "asset_id": "xhs-02-evidence",
                "role": "evidence",
                "target_pages": ["xhs-02"],
                "query": "AI research lab",
                "preferred_recipe": "M10",
                "candidates": [
                    {
                        "provider": "pexels",
                        "image_url": "https://images.example/lab.png",
                        "source_url": "https://pexels.example/photo/lab",
                        "author": "Ada",
                        "license_status": "pexels-license",
                    }
                ],
            }
        ],
    }

    materialized = materialize_image_assets(
        plan,
        tmp_path / "assets",
        image_asset_mode="download",
        fetch_json=lambda *_args, **_kwargs: {},
        fetch_bytes=lambda _url: (_png_bytes(), "image/png"),
    )

    selected = materialized["selected_assets"][0]
    assert selected["status"] == "available"
    assert selected["render_path"] == "assets/images/xhs-02-evidence.png"
    assert selected["target_pages"] == ["xhs-02"]
    assert selected["target_insight_index"] is None
    assert (tmp_path / "assets" / "images" / "xhs-02-evidence.png").exists()
    sources = (tmp_path / "assets" / "SOURCES.md").read_text(encoding="utf-8")
    assert "已下载外部素材" in sources
    assert "https://pexels.example/photo/lab" in sources


def test_materialize_image_assets_avoids_reusing_same_web_candidate(tmp_path):
    shared_candidates = [
        {
            "candidate_id": "cand-1",
            "provider": "unsplash",
            "image_url": "https://images.example/window-1.jpg",
            "source_url": "https://unsplash.example/photo/window-1",
            "author": "Ada",
            "license_status": "unsplash-license",
        },
        {
            "candidate_id": "cand-2",
            "provider": "unsplash",
            "image_url": "https://images.example/window-2.jpg",
            "source_url": "https://unsplash.example/photo/window-2",
            "author": "Grace",
            "license_status": "unsplash-license",
        },
    ]
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [],
        "requests": [
            {
                "asset_id": "xhs-02-evidence",
                "role": "evidence",
                "target_pages": ["xhs-02"],
                "query": "person alone by window",
                "preferred_recipe": "M10",
                "candidates": shared_candidates,
            },
            {
                "asset_id": "xhs-08-evidence",
                "role": "evidence",
                "target_pages": ["xhs-08"],
                "query": "person alone by window",
                "preferred_recipe": "M10",
                "candidates": shared_candidates,
            },
        ],
    }

    materialized = materialize_image_assets(
        plan,
        tmp_path / "assets",
        image_asset_mode="download",
        fetch_json=lambda *_args, **_kwargs: {},
        fetch_bytes=lambda _url: (_png_bytes(), "image/png"),
    )

    assert [request["selected_candidate_id"] for request in materialized["requests"]] == ["cand-1", "cand-2"]
    assert [asset["source_url"] for asset in materialized["selected_assets"]] == [
        "https://unsplash.example/photo/window-1",
        "https://unsplash.example/photo/window-2",
    ]


def test_materialize_image_assets_plan_does_not_generate_concept_fallback(tmp_path):
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [],
        "requests": [
            {
                "asset_id": "xhs-02-evidence",
                "role": "evidence",
                "target_pages": ["xhs-02"],
                "query": "computer vision lab",
                "preferred_recipe": "M10",
            }
        ],
    }

    materialized = materialize_image_assets(plan, tmp_path / "assets")

    assert materialized["selected_assets"] == []
    assert materialized["requests"][0].get("status") is None
    assert not (tmp_path / "assets" / "images" / "xhs-02-evidence.svg").exists()
