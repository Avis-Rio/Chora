"""vision_subject_mapper 测试（env 关时跳过真实 API）。"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from distribution_pipeline.renderers.guizang.vision_subject_mapper import (
    VISION_DEFAULT_MAX_PER_PACKAGE,
    build_vision_subject_map,
    call_gemini_vision,
    call_vision_for_pages,
    merge_vision_into_subject_map,
    vision_cache_lookup,
    vision_cache_remember,
    vision_concurrency,
    vision_disabled,
    vision_max_per_package,
    vision_timeout,
    _extract_json_blob,
    _image_hash,
    _load_gemini_config,
    _normalize_vision_output,
)


# -----------------------------------------------------------------------------
# 1. env 开关
# -----------------------------------------------------------------------------


def test_vision_disabled_default_true(monkeypatch):
    monkeypatch.delenv("CHORA_DISTRIBUTION_VISION_PROVIDER", raising=False)
    assert vision_disabled() is True


@pytest.mark.parametrize("value", ["none", "off", "false", "0", ""])
def test_vision_disabled_env(monkeypatch, value):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", value)
    assert vision_disabled() is True


def test_vision_disabled_env_gemini_enables_vision(monkeypatch):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", "gemini")
    assert vision_disabled() is False


def test_vision_concurrency_default(monkeypatch):
    monkeypatch.delenv("CHORA_DISTRIBUTION_VISION_CONCURRENCY", raising=False)
    assert vision_concurrency() == 1


def test_vision_concurrency_clamped(monkeypatch):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_CONCURRENCY", "5")
    assert vision_concurrency() == 5


def test_vision_max_per_package_default(monkeypatch):
    monkeypatch.delenv("CHORA_DISTRIBUTION_VISION_MAX_PER_PACKAGE", raising=False)
    assert vision_max_per_package() == VISION_DEFAULT_MAX_PER_PACKAGE == 4


def test_vision_timeout_default(monkeypatch):
    monkeypatch.delenv("CHORA_DISTRIBUTION_VISION_TIMEOUT", raising=False)
    assert vision_timeout() == 60


# -----------------------------------------------------------------------------
# 2. JSON 解析容错
# -----------------------------------------------------------------------------


def test_extract_json_blob_parses_plain_json():
    text = '{"primary_subject": {"type": "portrait"}}'
    assert _extract_json_blob(text) == {"primary_subject": {"type": "portrait"}}


def test_extract_json_blob_strips_fenced_markdown():
    text = "```json\n{\"primary_subject\": {\"type\": \"landscape\"}}\n```"
    assert _extract_json_blob(text) == {"primary_subject": {"type": "landscape"}}


def test_extract_json_blob_handles_surrounding_text():
    text = "Here is the analysis:\n{\"primary_subject\": {\"type\": \"food\"}}\nDone."
    result = _extract_json_blob(text)
    assert result == {"primary_subject": {"type": "food"}}


def test_extract_json_blob_returns_none_for_invalid():
    assert _extract_json_blob("not json at all") is None
    assert _extract_json_blob("") is None


# -----------------------------------------------------------------------------
# 3. _normalize_vision_output
# -----------------------------------------------------------------------------


def test_normalize_vision_output_complete_input():
    raw = {
        "primary_subject": {
            "type": "portrait",
            "label": "人像",
            "face_present": True,
            "focal_feature": "face center",
            "face_position": {"x_pct": 70, "y_pct": 30},
            "silhouette_edge": {"left_pct": 50, "right_pct": 95, "top_pct": 5, "bottom_pct": 85},
        },
        "quiet_zone": {
            "x_pct": 0, "y_pct": 70, "width_pct": 35, "height_pct": 25,
            "passes_quiet_zone_test": True,
            "description": "lower-left uniform fog",
        },
        "light": {"passes_light_test": True, "type": "overcast"},
        "safe_text_zone": "above-below",
        "object_position": "center 50%",
        "recommendation": {"text_can_overlay": True, "reason": "ample quiet zone"},
    }
    smap = _normalize_vision_output(raw)
    assert smap["vision_present"] is True
    assert smap["type"] == "portrait"
    assert smap["face"] is True
    assert smap["face_position"] == {"x_pct": 70.0, "y_pct": 30.0}
    assert smap["silhouette_edge"]["left_pct"] == 50.0
    assert smap["quiet_zone_rect"]["width_pct"] == 35.0
    assert smap["safe_zone"] == "above-below"
    assert smap["object_position"] == "center 50%"
    assert smap["passes_quiet_zone"] is True
    assert smap["passes_light"] is True
    assert smap["requires_localized_tint"] is False
    assert smap["text_can_overlay"] is True


def test_normalize_vision_output_clamps_invalid_pcts():
    raw = {
        "primary_subject": {
            "type": "abstract",
            "face_position": {"x_pct": 150, "y_pct": -20},
            "silhouette_edge": {"left_pct": "bad", "right_pct": 200, "top_pct": None, "bottom_pct": 50},
        },
        "quiet_zone": {"x_pct": "x", "y_pct": 50, "width_pct": -10, "height_pct": 200},
    }
    smap = _normalize_vision_output(raw)
    assert smap["face_position"] == {"x_pct": 100.0, "y_pct": 0.0}
    assert smap["silhouette_edge"]["left_pct"] == 0.0
    assert smap["silhouette_edge"]["right_pct"] == 100.0
    assert smap["silhouette_edge"]["top_pct"] == 0.0
    assert smap["quiet_zone_rect"]["x_pct"] == 0.0
    assert smap["quiet_zone_rect"]["width_pct"] == 0.0
    assert smap["quiet_zone_rect"]["height_pct"] == 100.0


def test_normalize_vision_output_invalid_safe_zone_falls_back():
    raw = {
        "primary_subject": {"type": "object"},
        "safe_text_zone": "made-up-zone",
        "object_position": "made-up-pos",
    }
    smap = _normalize_vision_output(raw)
    assert smap["safe_zone"] == "above-below"
    assert smap["object_position"] == "center 50%"


def test_normalize_vision_output_empty_input():
    smap = _normalize_vision_output({})
    assert smap["vision_present"] is True
    assert smap["type"] == "abstract"
    assert smap["label"] == "抽象"
    assert smap["face"] is False
    assert smap["safe_zone"] == "above-below"
    assert smap["object_position"] == "center 50%"


# -----------------------------------------------------------------------------
# 4. 缓存
# -----------------------------------------------------------------------------


def test_image_hash_stable(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 100)
    h1 = _image_hash(img)
    h2 = _image_hash(img)
    assert h1 == h2


def test_vision_cache_lookup_miss_when_empty(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert vision_cache_lookup(tmp_path, img) is None


def test_vision_cache_lookup_hit(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    vision_cache_remember(tmp_path, img, {"vision_present": True, "type": "portrait"})
    cached = vision_cache_lookup(tmp_path, img)
    assert cached is not None
    assert cached["_cache_hit"] is True
    assert cached["type"] == "portrait"


# -----------------------------------------------------------------------------
# 5. 合并 vision + 启发式
# -----------------------------------------------------------------------------


def test_merge_vision_into_subject_map_overrides_coordinates():
    heuristic = {
        "type": "abstract",
        "label": "抽象",
        "face": False,
        "focus": "primary subject",
        "safe_zone": "above-below",
        "object_position": "center 50%",
        "passes_quiet_zone": False,
        "passes_light": False,
        "requires_localized_tint": True,
        "auto_generated": True,
    }
    vision = {
        "vision_present": True,
        "type": "portrait",
        "label": "人像",
        "face": True,
        "focus": "face center",
        "face_position": {"x_pct": 70.0, "y_pct": 30.0},
        "silhouette_edge": {"left_pct": 50.0, "right_pct": 95.0, "top_pct": 5.0, "bottom_pct": 85.0},
        "quiet_zone_rect": {"x_pct": 0.0, "y_pct": 70.0, "width_pct": 35.0, "height_pct": 25.0},
        "safe_zone": "one-side",
        "object_position": "center 25%",
        "passes_quiet_zone": True,
        "passes_light": True,
        "requires_localized_tint": False,
        "text_can_overlay": True,
    }
    merged = merge_vision_into_subject_map(heuristic, vision)
    assert merged["type"] == "portrait"
    assert merged["label"] == "人像"
    assert merged["face"] is True
    assert merged["face_position"] == {"x_pct": 70.0, "y_pct": 30.0}
    assert merged["safe_zone"] == "one-side"
    assert merged["object_position"] == "center 25%"
    assert merged["passes_quiet_zone"] is True
    assert merged["passes_light"] is True
    assert merged["vision_enhanced"] is True
    assert merged["text_can_overlay"] is True  # default
    assert merged["auto_generated"] is False  # vision 看过


def test_merge_vision_with_safe_zone_none_falls_back_to_heuristic():
    heuristic = {"safe_zone": "above-below", "type": "abstract", "label": "抽象", "face": False}
    vision = {"vision_present": True, "safe_zone": "none", "type": "object"}
    merged = merge_vision_into_subject_map(heuristic, vision)
    assert merged["safe_zone"] == "above-below"  # 启发式保留


def test_merge_vision_without_vision_present_returns_heuristic():
    heuristic = {"safe_zone": "above-below", "type": "landscape"}
    vision = {"vision_present": False}
    merged = merge_vision_into_subject_map(heuristic, vision)
    assert merged == heuristic


# -----------------------------------------------------------------------------
# 6. build_vision_subject_map（mock Gemini）
# -----------------------------------------------------------------------------


def test_build_vision_subject_map_returns_none_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", "none")
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert build_vision_subject_map(img) is None


def test_build_vision_subject_map_returns_cached(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    vision_cache_remember(tmp_path, img, {"vision_present": True, "type": "landscape"})
    smap = build_vision_subject_map(img, cache_dir=tmp_path)
    assert smap is not None
    assert smap["type"] == "landscape"
    assert smap.get("_cache_hit") is True


def test_build_vision_subject_map_calls_gemini_and_normalizes(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", "gemini")
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    fake_response = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": json.dumps({
                        "primary_subject": {
                            "type": "portrait",
                            "label": "人像",
                            "face_present": True,
                            "face_position": {"x_pct": 50, "y_pct": 30},
                            "silhouette_edge": {"left_pct": 30, "right_pct": 80, "top_pct": 0, "bottom_pct": 100},
                        },
                        "quiet_zone": {"passes_quiet_zone_test": True, "description": "sky top"},
                        "light": {"passes_light_test": True, "type": "overcast"},
                        "safe_text_zone": "above-below",
                        "object_position": "center 25%",
                        "recommendation": {"text_can_overlay": True, "reason": "ok"},
                    })
                }]
            }
        }]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response

    with patch("distribution_pipeline.renderers.guizang.vision_subject_mapper._post_gemini_request", return_value=mock_resp):
        smap = build_vision_subject_map(img, cache_dir=tmp_path)

    assert smap is not None
    assert smap["type"] == "portrait"
    assert smap["face"] is True
    assert smap["object_position"] == "center 25%"
    # 第二次调用应命中缓存，不再调 Gemini
    with patch("distribution_pipeline.renderers.guizang.vision_subject_mapper._post_gemini_request") as mock_post:
        cached = build_vision_subject_map(img, cache_dir=tmp_path)
    assert cached is not None
    assert mock_post.call_count == 0


def test_build_vision_subject_map_returns_none_on_api_error(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", "gemini")
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "rate limited"
    with patch("distribution_pipeline.renderers.guizang.vision_subject_mapper._post_gemini_request", return_value=mock_resp):
        assert build_vision_subject_map(img, cache_dir=tmp_path) is None


def test_build_vision_subject_map_returns_none_on_invalid_json(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", "gemini")
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}
    with patch("distribution_pipeline.renderers.guizang.vision_subject_mapper._post_gemini_request", return_value=mock_resp):
        assert build_vision_subject_map(img, cache_dir=tmp_path) is None


# -----------------------------------------------------------------------------
# 7. 批量并发
# -----------------------------------------------------------------------------


def test_call_vision_for_pages_disabled_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", "none")
    images = [tmp_path / f"x{i}.png" for i in range(3)]
    for img in images:
        img.write_bytes(b"\x89PNG\r\n\x1a\n")
    results = call_vision_for_pages(images, tmp_path, max_per_package=4)
    assert len(results) == 3
    assert all(smap is None for _, smap in results)


def test_call_vision_for_pages_respects_quota(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", "gemini")
    images = [tmp_path / f"x{i}.png" for i in range(5)]
    for img in images:
        img.write_bytes(b"\x89PNG\r\n\x1a\n")

    # max_per_package=2 → 只前 2 张尝试 vision
    with patch("distribution_pipeline.renderers.guizang.vision_subject_mapper._post_gemini_request") as mock_post:
        # 模拟 vision 失败（返回 None）
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "fail"
        mock_post.return_value = mock_resp
        results = call_vision_for_pages(images, tmp_path, max_per_package=2)
    # 后 3 张直接 None（不调）
    assert results[0][1] is None  # 第 1 张：调了但失败
    assert results[1][1] is None  # 第 2 张：调了但失败
    assert results[2][1] is None  # 第 3 张：未调（配额外）
    assert results[3][1] is None
    assert results[4][1] is None


def test_call_vision_for_pages_serial_concurrency(tmp_path, monkeypatch):
    """concurrency=1 走串行。"""
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_CONCURRENCY", "1")
    monkeypatch.setenv("CHORA_DISTRIBUTION_VISION_PROVIDER", "gemini")
    images = [tmp_path / f"x{i}.png" for i in range(2)]
    for img in images:
        img.write_bytes(b"\x89PNG\r\n\x1a\n")

    with patch("distribution_pipeline.renderers.guizang.vision_subject_mapper.build_vision_subject_map", return_value=None) as mock_bv:
        call_vision_for_pages(images, tmp_path, max_per_package=2, concurrency=1)
    assert mock_bv.call_count == 2


# -----------------------------------------------------------------------------
# 8. _load_gemini_config 错误路径
# -----------------------------------------------------------------------------


def test_load_gemini_config_missing_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    missing = tmp_path / "no-such-sources.yaml"
    with pytest.raises(RuntimeError, match="未找到"):
        _load_gemini_config(config_path=missing)
