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
    insights[4] = {
        "index": 5,
        "title": "互惠原则是社交增长的底层机制",
        "one_liner": "持续给予价值会自然激活回馈。",
    }
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
        {"index": index, "title": f"洞察{index}", "one_liner": "独处不等于失败。"} for index in range(1, 8)
    ]
    insights[0] = {"index": 1, "title": "孤独的历史性转变", "one_liner": "孤独曾是被尊重的主动选择。"}
    insights[4] = {"index": 5, "title": "外在动机对身份的侵蚀", "one_liner": "社交媒体把分享变成表演。"}
    insights[6] = {
        "index": 7,
        "title": "孤独与孤寂的根本区别",
        "one_liner": "孤独是主动选择，孤寂是连接痛苦。",
    }

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
        {"index": index, "title": f"洞察{index}", "one_liner": "独处不等于失败。"} for index in range(1, 8)
    ]
    insights[0] = {"index": 1, "title": "孤独的历史性转变", "one_liner": "孤独曾是被尊重的主动选择。"}
    insights[2] = {
        "index": 3,
        "title": "第三空间的政治经济学",
        "one_liner": "公共空间消失后，偶遇失去物理基础。",
    }
    insights[4] = {"index": 5, "title": "外在动机对身份的侵蚀", "one_liner": "社交媒体把分享变成表演。"}

    plan = build_image_asset_plan(
        {"title": "Why People Disappear | The Psychology of Being Alone", "tags": ["Psychology"]},
        insights,
        [],
        {"visual_motifs": []},
        content_dir,
    )

    evidence_insights = [
        request["target_insight_index"] for request in plan["requests"] if request["role"] == "evidence"
    ]
    evidence_queries = [request["query"] for request in plan["requests"] if request["role"] == "evidence"]

    assert evidence_insights[:3] == [1, 3, 5]
    assert "quiet city cafe library" in evidence_queries


def test_build_image_asset_plan_spaces_evidence_requests_across_long_deck():
    content_dir = Path("tests/fixtures/content_archive/2026-05-13/youtube_硅谷101_Token经济学")
    insights = [
        {"index": index, "title": f"洞察{index}", "one_liner": "数据筛选是护城河"} for index in range(1, 11)
    ]

    plan = build_image_asset_plan(
        {"title": "谷歌AI的14年", "tags": []},
        insights,
        [],
        {"visual_motifs": []},
        content_dir,
    )

    evidence_targets = [
        request["target_pages"][0] for request in plan["requests"] if request["role"] == "evidence"
    ]
    evidence_insights = [
        request["target_insight_index"] for request in plan["requests"] if request["role"] == "evidence"
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


# ---------------------------------------------------------------------------
# Local variant derivation (2026-07-12): when a usable cover exists,
# PIL crops the cover into 4 evidence variants bound to the planner's
# evidence offsets, so daily rewrites no longer need to download
# external imagery to populate evidence pages.
# ---------------------------------------------------------------------------


def _write_cover(tmp_path: Path) -> Path:
    """Write a real, PIL-readable cover image (>= 320x320) for variant derivation."""
    from PIL import Image

    cover = tmp_path / "content" / "cover.jpg"
    cover.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (640, 480), color=(180, 60, 90))
    img.save(cover, format="JPEG", quality=85)
    return cover


def test_generate_local_variants_writes_four_evidence_images(tmp_path):
    cover = _write_cover(tmp_path)
    source = {
        "asset_id": "source-cover",
        "role": "hero",
        "source_type": "local",
        "source_path": str(cover),
    }
    from distribution_pipeline.assets.image_assets import _generate_local_variants

    images_dir = tmp_path / "images"
    variants = _generate_local_variants(source, images_dir, evidence_offsets=[0, 1, 2, 3])

    assert len(variants) == 4
    variant_names = {v["variant"] for v in variants}
    assert variant_names == {"hero", "top", "bottom", "blur"}

    crops_dir = images_dir / "source-crops"
    assert crops_dir.exists()
    # Every declared variant file must exist on disk.
    for v in variants:
        assert (crops_dir / v["filename"]).exists()
        assert v["status"] == "available"
        assert v["license_status"] == "source-provided"
        # render_path is package-relative for downstream consumers.
        assert v["render_path"].startswith("assets/images/source-crops/")
    # PIL-derived bytes must be non-trivial JPEG.
    hero_bytes = (crops_dir / "source-cover-hero.jpg").read_bytes()
    assert hero_bytes[:2] == b"\xff\xd8", "hero variant must be a real JPEG"


def test_generate_local_variants_binds_to_evidence_offsets(tmp_path):
    cover = _write_cover(tmp_path)
    source = {"asset_id": "cover", "source_path": str(cover)}
    from distribution_pipeline.assets.image_assets import _generate_local_variants

    variants = _generate_local_variants(source, tmp_path / "images", evidence_offsets=[2, 5, 7, 9])
    # Each variant carries the offset it should bind to in the planner.
    seen = {v["variant"]: v["target_insight_index"] for v in variants}
    assert seen == {"hero": 2, "top": 5, "bottom": 7, "blur": 9}


def test_generate_local_variants_returns_empty_when_cover_missing(tmp_path):
    source = {"asset_id": "cover", "source_path": str(tmp_path / "no_such.jpg")}
    from distribution_pipeline.assets.image_assets import _generate_local_variants

    assert _generate_local_variants(source, tmp_path / "images", []) == []


def test_materialize_auto_mode_with_local_cover_uses_plan(tmp_path):
    """image_asset_mode='auto' with a usable cover must resolve to 'plan'
    and emit four derived evidence variants — never fall through to
    network calls."""
    cover = _write_cover(tmp_path)
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [
            {
                "asset_id": "source-cover",
                "role": "hero",
                "source_type": "local",
                "status": "available",
                "source_path": str(cover),
                "target_pages": ["xhs-01"],
            }
        ],
        "requests": [
            {
                "asset_id": "xhs-02-evidence",
                "role": "evidence",
                "target_pages": ["xhs-02"],
                "query": "research lab",
                "preferred_recipe": "M10",
                "target_insight_index": 1,
            },
            {
                "asset_id": "xhs-03-evidence",
                "role": "evidence",
                "target_pages": ["xhs-03"],
                "query": "focused creator",
                "preferred_recipe": "M11",
                "target_insight_index": 2,
            },
        ],
    }

    materialized = materialize_image_assets(plan, tmp_path / "assets", image_asset_mode="auto")

    # Auto should resolve to plan when a local cover exists.
    assert materialized["resolved_mode"] == "plan"
    # 1 original cover + 4 derived variants = 5 local_assets.
    derived = [a for a in materialized["local_assets"] if a.get("source_type") == "local-variant"]
    assert len(derived) == 4
    # Variants must bind to the planner's evidence offsets.
    targets = sorted(a["target_insight_index"] for a in derived if a.get("target_insight_index") is not None)
    assert targets == [1, 2]
    # And the variant files must actually be on disk.
    # render_path is package-relative and already starts with
    # "assets/images/source-crops/...", so resolve it directly
    # against tmp_path (which IS the package root in this test).
    for asset in derived:
        full = tmp_path / asset["render_path"]
        assert full.exists(), f"variant file missing: {full}"


def test_materialize_auto_mode_without_cover_resolves_to_candidates(tmp_path):
    """image_asset_mode='auto' with NO local cover must resolve to
    'candidates' so the planner at least gets external search URLs."""
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
                "query": "research lab",
                "preferred_recipe": "M10",
            }
        ],
    }

    materialized = materialize_image_assets(plan, tmp_path / "assets", image_asset_mode="auto")

    assert materialized["resolved_mode"] == "candidates"


def test_materialize_disable_local_variants_env(tmp_path, monkeypatch):
    """Operators can opt out of local variant derivation via env."""
    monkeypatch.setenv("CHORA_DISTRIBUTION_DISABLE_LOCAL_VARIANTS", "1")
    cover = _write_cover(tmp_path)
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [
            {
                "asset_id": "source-cover",
                "role": "hero",
                "source_type": "local",
                "status": "available",
                "source_path": str(cover),
                "target_pages": ["xhs-01"],
            }
        ],
        "requests": [],
    }

    materialized = materialize_image_assets(plan, tmp_path / "assets")

    # Original cover copied, but no derived variants.
    derived = [a for a in materialized["local_assets"] if a.get("source_type") == "local-variant"]
    assert derived == []
    assert not (tmp_path / "assets" / "images" / "source-crops").exists()


def test_materialize_writes_local_variants_to_sources_markdown(tmp_path):
    """SOURCES.md must list every derived variant so operators see the
    lineage back to the source cover."""
    cover = _write_cover(tmp_path)
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [
            {
                "asset_id": "source-cover",
                "role": "hero",
                "source_type": "local",
                "status": "available",
                "source_path": str(cover),
                "target_pages": ["xhs-01"],
            }
        ],
        "requests": [],
    }

    materialize_image_assets(plan, tmp_path / "assets")

    sources_md = (tmp_path / "assets" / "SOURCES.md").read_text(encoding="utf-8")
    for variant in ("hero", "top", "bottom", "blur"):
        assert variant in sources_md, f"SOURCES.md missing {variant} variant"


def test_materialize_does_not_recurse_into_derived_variants(tmp_path):
    """Regression: derive PIL variants only from the ORIGINAL cover,
    never from the freshly-derived ones. A previous bug mutated the
    ``local_assets`` list in-place inside the loop, causing exponential
    blow-up (each derived variant itself had ``status='available'`` and
    triggered another derivation pass).
    """
    cover = _write_cover(tmp_path)
    plan = {
        "version": 1,
        "status": "planned",
        "providers": {},
        "local_assets": [
            {
                "asset_id": "source-cover",
                "role": "hero",
                "source_type": "local",
                "status": "available",
                "source_path": str(cover),
                "target_pages": ["xhs-01"],
            }
        ],
        "requests": [],
    }

    materialized = materialize_image_assets(plan, tmp_path / "assets")

    # 1 original cover + 4 derived variants = 5 entries — never more.
    assert len(materialized["local_assets"]) == 5, materialized["local_assets"]
    derived = [a for a in materialized["local_assets"] if a.get("source_type") == "local-variant"]
    assert len(derived) == 4
    # And every variant's source_path must point back at the original
    # cover, not at another derived variant.
    for variant in derived:
        assert variant["source_path"] == str(cover)
