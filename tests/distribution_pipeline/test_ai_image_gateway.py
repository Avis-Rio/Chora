"""戊项：C 通道 AI 生图兜底（Gemini gateway）测试。"""

import json

import pytest

from distribution_pipeline.assets.ai_image.gateway import (
    AI_COVERED_ROLES,
    AI_MAX_PER_PACKAGE,
    build_prompt,
    is_ai_disabled,
    lookup_cache,
    remember_in_cache,
    should_generate_via_ai,
)

# -----------------------------------------------------------------------------
# 1. should_generate_via_ai gate 决策
# -----------------------------------------------------------------------------


def test_should_generate_via_ai_skips_when_role_not_covered():
    request = {"role": "hero", "target_pages": ["xhs-01"]}
    assert should_generate_via_ai(request, []) is False


def test_should_generate_via_ai_triggers_for_evidence_with_no_visual():
    request = {"role": "evidence", "target_pages": ["xhs-02"]}
    assert should_generate_via_ai(request, []) is True


def test_should_generate_via_ai_triggers_for_cover_hero():
    request = {"role": "cover_hero", "target_pages": ["xhs-01"]}
    assert should_generate_via_ai(request, []) is True


def test_should_generate_via_ai_skips_when_visual_already_available():
    request = {"role": "evidence", "target_pages": ["xhs-02"]}
    selected = [
        {
            "status": "available",
            "provider": "pexels",
            "target_pages": ["xhs-02"],
        }
    ]
    assert should_generate_via_ai(request, selected) is False


def test_should_generate_via_ai_respects_disabled_flag():
    request = {"role": "evidence", "target_pages": ["xhs-02"]}
    assert should_generate_via_ai(request, [], ai_disabled=True) is False


def test_should_generate_via_ai_skips_when_target_pages_empty():
    request = {"role": "evidence", "target_pages": []}
    assert should_generate_via_ai(request, []) is False


# -----------------------------------------------------------------------------
# 2. 缓存命中
# -----------------------------------------------------------------------------


def test_lookup_cache_miss_when_no_cache_file(tmp_path):
    result = lookup_cache(
        tmp_path,
        role="evidence",
        query="computer vision lab",
        target_pages=["xhs-02"],
    )
    assert result is None


def test_lookup_cache_hit_when_file_exists(tmp_path):
    # 准备 cache
    (tmp_path / "xhs-02-evidence.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    remember_in_cache(
        tmp_path,
        role="evidence",
        query="computer vision lab",
        target_pages=["xhs-02"],
        theme=None,
        asset={
            "asset_id": "xhs-02-evidence",
            "filename": "xhs-02-evidence.png",
        },
    )

    result = lookup_cache(
        tmp_path,
        role="evidence",
        query="computer vision lab",
        target_pages=["xhs-02"],
    )

    assert result is not None
    assert result["provider"] == "chora-ai-generated"
    assert result["status"] == "available"
    assert result["cache_hit"] is True
    assert result["render_path"] == "assets/images/xhs-02-evidence.png"


def test_lookup_cache_different_query_misses(tmp_path):
    """同 role 但不同 query → 不同 hash → cache miss。"""
    (tmp_path / "xhs-02-evidence.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    remember_in_cache(
        tmp_path,
        role="evidence",
        query="computer vision lab",
        target_pages=["xhs-02"],
        theme=None,
        asset={"asset_id": "xhs-02-evidence", "filename": "xhs-02-evidence.png"},
    )
    result = lookup_cache(
        tmp_path,
        role="evidence",
        query="token economics",
        target_pages=["xhs-02"],
    )
    assert result is None


def test_lookup_cache_drops_entry_when_file_removed(tmp_path):
    """cache entry 存在但文件被删 → 视为 miss。"""
    remember_in_cache(
        tmp_path,
        role="evidence",
        query="x",
        target_pages=["xhs-02"],
        theme=None,
        asset={"asset_id": "xhs-02-evidence", "filename": "xhs-02-evidence.png"},
    )
    # 文件不存在
    result = lookup_cache(
        tmp_path,
        role="evidence",
        query="x",
        target_pages=["xhs-02"],
    )
    assert result is None


def test_remember_in_cache_persists_to_disk(tmp_path):
    remember_in_cache(
        tmp_path,
        role="evidence",
        query="q1",
        target_pages=["xhs-02"],
        theme="ink-classic",
        asset={"asset_id": "a1", "filename": "a1.png"},
    )
    cache_path = tmp_path / ".ai_image_cache.json"
    assert cache_path.exists()
    data = json.loads(cache_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and len(data) == 1
    entry = next(iter(data.values()))
    assert entry["asset_id"] == "a1"
    assert entry["filename"] == "a1.png"


# -----------------------------------------------------------------------------
# 3. build_prompt
# -----------------------------------------------------------------------------


def test_build_prompt_includes_role_visual_cue():
    p = build_prompt("mountain summit", role="cover_hero", category="travel", theme="kraft-paper")
    assert "Editorial travel" in p
    assert "hero composition" in p
    assert "kraft-paper palette" in p
    assert "mountain summit" in p
    assert "no text" in p
    assert "3:4" in p


def test_build_prompt_swiss_workplace_uses_ikb():
    p = build_prompt("team meeting", role="evidence", category="workplace", theme="ikb")
    assert "Swiss style" in p
    assert "IKB blue accent" in p
    assert "team meeting" in p


def test_build_prompt_fallback_for_unknown_category():
    p = build_prompt("abstract concept", role="evidence", category=None, theme=None)
    assert "Editorial concept" in p
    assert "abstract concept" in p


# -----------------------------------------------------------------------------
# 4. is_ai_disabled
# -----------------------------------------------------------------------------


def test_is_ai_disabled_default_false(monkeypatch):
    monkeypatch.delenv("CHORA_DISTRIBUTION_AI_IMAGE", raising=False)
    assert is_ai_disabled() is False


@pytest.mark.parametrize("value", ["0", "false", "False", "no", "off", "否", "不"])
def test_is_ai_disabled_respects_env(monkeypatch, value):
    monkeypatch.setenv("CHORA_DISTRIBUTION_AI_IMAGE", value)
    assert is_ai_disabled() is True


# -----------------------------------------------------------------------------
# 5. AI_MAX_PER_PACKAGE 配额（按上游 "AI 生图克制地用"）
# -----------------------------------------------------------------------------


def test_ai_max_per_package_is_2():
    """上游 production-workflow.md: 1-2 张为常规；戊项设为 2。"""
    assert AI_MAX_PER_PACKAGE == 2


def test_ai_covered_roles_includes_evidence_and_cover_hero():
    assert "evidence" in AI_COVERED_ROLES
    assert "cover_hero" in AI_COVERED_ROLES
    assert "hero" not in AI_COVERED_ROLES  # role=hero 不调 AI


# -----------------------------------------------------------------------------
# 6. 集成：materialize_image_assets plan 模式不调 AI
# -----------------------------------------------------------------------------


def test_materialize_image_assets_plan_mode_does_not_call_ai(tmp_path, monkeypatch):
    """plan 模式（默认）按 workflow-rules.md "Daily 后处理必须记录并继续" 不生图。"""
    from distribution_pipeline.assets.image_assets import materialize_image_assets

    called = {"n": 0}
    import distribution_pipeline.assets.image_assets as ia

    def fake_ai_fallback(*args, **kwargs):
        called["n"] += 1
        return args[0]

    monkeypatch.setattr(ia, "_ai_fallback", fake_ai_fallback)

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
            }
        ],
    }
    materialize_image_assets(plan, tmp_path / "assets", image_asset_mode="plan")

    assert called["n"] == 0  # plan 模式不调


def test_materialize_image_assets_candidates_mode_calls_ai(tmp_path, monkeypatch):
    """candidates 模式 → 调 AI 兜底（不调真实 API，由 monkeypatch 替换）。"""
    from distribution_pipeline.assets.image_assets import materialize_image_assets

    called = {"n": 0}
    captured = {}

    def fake_ai_fallback(materialized, images_dir, **kwargs):
        called["n"] += 1
        captured.update(kwargs)
        return materialized

    import distribution_pipeline.assets.image_assets as ia

    monkeypatch.setattr(ia, "_ai_fallback", fake_ai_fallback)

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
            }
        ],
    }
    materialize_image_assets(
        plan,
        tmp_path / "assets",
        image_asset_mode="candidates",
        category={"key": "workplace"},
        theme="ikb-dot-gradient",
    )

    assert called["n"] == 1
    assert captured["category"] == "workplace"
    assert captured["theme"] == "ikb-dot-gradient"
