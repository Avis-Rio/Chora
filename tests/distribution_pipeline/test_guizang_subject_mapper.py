"""丁项：主体映射（subject_map）启发式 + HTML 注释测试。"""

from distribution_pipeline.renderers.guizang.subject_mapper import (
    build_subject_map,
    classify_subject,
    passes_light_test,
    passes_quiet_zone,
    pick_object_position,
    pick_safe_zone,
    subject_map_html_comment,
)

# -----------------------------------------------------------------------------
# 1. classify_subject：主体类型推断
# -----------------------------------------------------------------------------


def test_classify_subject_detects_portrait_from_caption():
    image = {"caption": "executive portrait in office", "alt": "person face"}
    subject = classify_subject(image)
    assert subject["type"] == "portrait"
    assert subject["label"] == "人像"
    assert subject["face"] is True


def test_classify_subject_detects_full_body():
    image = {"caption": "ootd 全身穿搭", "filename": "outfit.png"}
    subject = classify_subject(image)
    assert subject["type"] == "full_body"
    assert subject["face"] is True


def test_classify_subject_detects_product():
    image = {"caption": "iPhone product shot", "asset_id": "iphone-15"}
    subject = classify_subject(image)
    assert subject["type"] == "product"


def test_classify_subject_detects_landscape():
    image = {"caption": "mountain summit at golden hour", "alt": "outdoor landscape"}
    subject = classify_subject(image)
    assert subject["type"] == "landscape"
    assert subject["face"] is False


def test_classify_subject_detects_cityscape():
    image = {"caption": "Tokyo skyline at night", "filename": "skyline.jpg"}
    subject = classify_subject(image)
    assert subject["type"] == "cityscape"


def test_classify_subject_detects_food():
    image = {"caption": "美食摆盘 餐厅氛围", "alt": "food dish"}
    subject = classify_subject(image)
    assert subject["type"] == "food"


def test_classify_subject_detects_animal():
    image = {"caption": "pet cat on sofa", "filename": "cat.jpg"}
    subject = classify_subject(image)
    assert subject["type"] == "animal"
    assert subject["face"] is True


def test_classify_subject_detects_3d_as_abstract():
    image = {"caption": "3d 渲染 mockup scene", "alt": "cgi render"}
    subject = classify_subject(image)
    assert subject["type"] == "abstract"


def test_classify_subject_falls_back_to_abstract_when_empty():
    subject = classify_subject({}, {"role": "evidence"})
    assert subject["type"] == "abstract"
    assert subject["hit_keyword"] is None


def test_classify_subject_uses_page_role_as_fallback_signal():
    """若 image metadata 缺失，page role 'cover' 或 'evidence' 不应误判。"""
    image = {}
    page = {"role": "cover", "title": "Wukong"}
    subject = classify_subject(image, page)
    # title "Wukong" 不在 SUBJECT_KEYWORDS；role "cover" 不在；fallback abstract
    assert subject["type"] in {"abstract", "object"}


# -----------------------------------------------------------------------------
# 2. passes_quiet_zone / passes_light_test
# -----------------------------------------------------------------------------


def test_passes_quiet_zone_for_landscape_with_sky_hint():
    image = {"caption": "fog over mountain", "filename": "mountain.jpg"}
    assert passes_quiet_zone(image) is True


def test_passes_quiet_zone_rejects_tight_portrait():
    image = {"caption": "tight portrait face crop", "filename": "face.jpg"}
    assert passes_quiet_zone(image) is False


def test_passes_quiet_zone_rejects_empty_metadata():
    assert passes_quiet_zone({}, {"role": "evidence"}) is False


def test_passes_light_test_for_atmospheric_hint():
    image = {"caption": "fog at dawn", "filename": "a.jpg"}
    assert passes_light_test(image) is True


def test_passes_light_test_rejects_high_saturation_noon():
    image = {"caption": "正午 高饱和 游客照", "filename": "b.jpg"}
    assert passes_light_test(image) is False


def test_passes_light_test_rejects_empty_metadata():
    assert passes_light_test({}, {"role": "evidence"}) is False


# -----------------------------------------------------------------------------
# 3. pick_safe_zone / pick_object_position
# -----------------------------------------------------------------------------


def test_pick_safe_zone_portrait_uses_one_side():
    subject = {"type": "portrait"}
    assert pick_safe_zone(subject) == "one-side"


def test_pick_safe_zone_landscape_uses_above_below():
    subject = {"type": "landscape"}
    assert pick_safe_zone(subject) == "above-below"


def test_pick_safe_zone_food_uses_above_below():
    subject = {"type": "food"}
    assert pick_safe_zone(subject) == "above-below"


def test_pick_safe_zone_animal_uses_one_side():
    subject = {"type": "animal"}
    assert pick_safe_zone(subject) == "one-side"


def test_pick_object_position_upper_third():
    assert pick_object_position({"type": "portrait"}, "upper") == "center 25%"


def test_pick_object_position_middle_default():
    assert pick_object_position({"type": "abstract"}) == "center 50%"


def test_pick_object_position_lower_third():
    assert pick_object_position({"type": "object"}, "lower") == "center 70%"


def test_pick_object_position_cityscape_uses_horizon_bias():
    """城市天际线 → 默认 center 35%（保留 horizon line）。"""
    assert pick_object_position({"type": "cityscape"}) == "center 35%"


# -----------------------------------------------------------------------------
# 4. build_subject_map：完整字段
# -----------------------------------------------------------------------------


def test_build_subject_map_returns_full_schema():
    image = {"caption": "executive portrait in office", "filename": "face.jpg"}
    page = {"role": "cover", "title": "CEO interview"}
    smap = build_subject_map(image, page)

    # 必含字段
    for key in (
        "type",
        "label",
        "face",
        "focus",
        "safe_zone",
        "quiet_zone",
        "light",
        "object_position",
        "passes_quiet_zone",
        "passes_light",
        "requires_localized_tint",
    ):
        assert key in smap, f"missing key: {key}"

    assert smap["type"] == "portrait"
    assert smap["face"] is True
    assert smap["safe_zone"] == "one-side"
    assert smap["object_position"] == "center 50%"


def test_build_subject_map_landscape_passes_both_tests():
    image = {"caption": "fog over mountain at dawn", "filename": "mountain.jpg"}
    smap = build_subject_map(image)
    assert smap["type"] == "landscape"
    assert smap["passes_quiet_zone"] is True
    assert smap["passes_light"] is True
    assert smap["requires_localized_tint"] is False
    assert smap["safe_zone"] == "above-below"


def test_build_subject_map_tight_portrait_fails_both_tests():
    image = {"caption": "tight portrait face", "filename": "face.jpg"}
    smap = build_subject_map(image)
    assert smap["passes_quiet_zone"] is False
    assert smap["requires_localized_tint"] is True


def test_build_subject_map_detects_vertical_third_from_caption():
    image = {"caption": "face top of frame, sky at bottom", "filename": "p.jpg"}
    smap = build_subject_map(image)
    # 'top' 命中 upper third hints
    assert smap["object_position"] == "center 25%"


def test_build_subject_map_handles_empty_metadata_gracefully():
    smap = build_subject_map({}, {"role": "cover"})
    assert smap["type"] == "abstract"
    assert smap["passes_quiet_zone"] is False  # 兜底
    assert smap["requires_localized_tint"] is True


def test_build_subject_map_with_image_path_defaults_to_heuristic_when_vision_off(tmp_path, monkeypatch):
    monkeypatch.delenv("CHORA_DISTRIBUTION_VISION_PROVIDER", raising=False)
    image_path = tmp_path / "landscape.jpg"
    image_path.write_bytes(b"fake")

    smap = build_subject_map(
        {"caption": "mountain valley with quiet sky"},
        {"role": "cover"},
        image_path=image_path,
        cache_dir=tmp_path,
    )

    assert smap["type"] == "landscape"
    assert smap.get("vision_enhanced") is not True


# -----------------------------------------------------------------------------
# 5. subject_map_html_comment：HTML 注释渲染
# -----------------------------------------------------------------------------


def test_subject_map_html_comment_renders_well_formed_comment():
    smap = build_subject_map({"caption": "mountain at dawn", "filename": "m.jpg"})
    html = subject_map_html_comment(smap, page_label="cover hero")

    assert html.startswith("<!-- subject map")
    assert "cover hero" in html
    assert "focus:" in html
    assert "safe text zone:" in html
    assert "object-position:" in html
    assert "thumbnail policy:" in html
    assert html.endswith("-->")


def test_subject_map_html_comment_escapes_xss_in_values():
    smap = {"focus": "<script>alert(1)</script>", "safe_zone": "above-below"}
    html = subject_map_html_comment(smap)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_subject_map_html_comment_returns_empty_for_none():
    assert subject_map_html_comment({}) == ""
    assert subject_map_html_comment(None) == ""


# -----------------------------------------------------------------------------
# 6. 集成：page_planner 写 subject_map 后 recipes 可读
# -----------------------------------------------------------------------------


def test_page_planner_writes_subject_map_via_asset_for_page():
    """_asset_for_page 在 asset 缺 subject_map 时自动生成。"""
    from distribution_pipeline.renderers.guizang.page_planner import _asset_for_page

    image_assets = {
        "local_assets": [
            {
                "asset_id": "a-01",
                "render_path": "assets/images/a.jpg",
                "caption": "mountain at dawn",  # landscape hint
                "role": "evidence",
                "status": "available",
                "target_pages": ["xhs-02"],
            }
        ],
        "selected_assets": [],
        "requests": [],
    }

    image = _asset_for_page(image_assets, "xhs-02")
    assert image is not None
    assert "subject_map" in image
    assert image["subject_map"]["type"] == "landscape"
    assert image["subject_map"]["passes_quiet_zone"] is True


def test_page_planner_preserves_existing_subject_map_from_asset():
    from distribution_pipeline.renderers.guizang.page_planner import _asset_for_page

    existing_sm = {"type": "portrait", "label": "人像", "face": True, "focus": "upper-center"}
    image_assets = {
        "local_assets": [
            {
                "asset_id": "a-01",
                "render_path": "assets/images/a.jpg",
                "caption": "unknown caption",
                "role": "cover",
                "status": "available",
                "target_pages": ["xhs-01"],
                "subject_map": existing_sm,
            }
        ],
        "selected_assets": [],
        "requests": [],
    }

    image = _asset_for_page(image_assets, "xhs-01")
    assert image["subject_map"] == existing_sm
