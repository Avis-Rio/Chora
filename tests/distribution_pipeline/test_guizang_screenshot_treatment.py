"""丙项：截图四件套（.frame-shot 六参数 + device 包裹）测试。"""

from distribution_pipeline.renderers.guizang.screenshot_treatment import (
    decide_screenshot_params,
    detect_screenshot,
    render_image_frame,
    render_screenshot_frame,
)

# -----------------------------------------------------------------------------
# 1. detect_screenshot：关键词命中
# -----------------------------------------------------------------------------


def test_detect_screenshot_hits_on_screenshot_keyword():
    assert detect_screenshot({"caption": "Linear app screenshot", "asset_id": "xhs-02"}) is True


def test_detect_screenshot_hits_on_app_shot():
    assert detect_screenshot({"alt": "app shot inside wechat", "filename": "screenshot.png"}) is True


def test_detect_screenshot_hits_on_dashboard_caption():
    assert detect_screenshot({"caption": "Notion dashboard view", "role": "evidence"}) is True


def test_detect_screenshot_hits_on_code_or_ide():
    assert detect_screenshot({"alt": "VSCode editor with file open"}) is True


def test_detect_screenshot_hits_on_terminal():
    assert detect_screenshot({"caption": "Terminal output of pytest run"}) is True


def test_detect_screenshot_hits_on_browser_capture():
    assert (
        detect_screenshot({"alt": "browser screenshot of the dashboard", "filename": "capture.png"}) is True
    )


def test_detect_screenshot_hits_on_chinese_hint():
    assert detect_screenshot({"caption": "微信应用截图"}) is True


def test_detect_screenshot_hits_on_console():
    assert detect_screenshot({"alt": "console output captured"}) is True


# -----------------------------------------------------------------------------
# 2. detect_screenshot：摄影/插画强提示拒绝
# -----------------------------------------------------------------------------


def test_detect_screenshot_rejects_portrait_over_screenshot_string():
    """即使 caption 含 'screenshot' 但有人像提示，仍判为摄影（不被视作截图）。"""
    assert detect_screenshot({"caption": "portrait screenshot of CEO", "alt": "executive portrait"}) is False


def test_detect_screenshot_rejects_food_photography():
    assert (
        detect_screenshot({"caption": "food photography for magazine cover", "asset_id": "dish-01"}) is False
    )


def test_detect_screenshot_rejects_landscape():
    assert (
        detect_screenshot({"caption": "scenery landscape of mountain", "filename": "mountain.jpg"}) is False
    )


def test_detect_screenshot_rejects_3d_render():
    assert detect_screenshot({"caption": "3d render of product mockup", "alt": "render"}) is False


def test_detect_screenshot_rejects_empty_metadata():
    assert detect_screenshot({}, {"role": "evidence"}) is False


# -----------------------------------------------------------------------------
# 3. decide_screenshot_params：6 参数决策
# -----------------------------------------------------------------------------


def test_decide_screenshot_params_swiss_default_uses_grey1_no_shadow():
    image = {"caption": "Linear dashboard", "asset_id": "xhs-02"}
    page = {"role": "evidence"}
    params = decide_screenshot_params(image, page, mode="swiss", theme="ikb")

    assert params["ratio"] == "16x10"
    assert params["corners"] == "sq"
    assert params["bg"] == "bg-grey-1"
    assert params["shadow"] == "none"
    assert params["inset"] == "sub"
    assert params["device"] is None
    assert params["asset_bg"] is None


def test_decide_screenshot_params_editorial_warm_paper2_soft_shadow():
    image = {"caption": "Notion page", "asset_id": "xhs-02"}
    page = {"role": "evidence"}
    params = decide_screenshot_params(image, page, mode="editorial", theme="ink-classic")

    assert params["ratio"] == "16x10"
    assert params["corners"] == "sm"
    assert params["bg"] == "bg-paper-2"
    assert params["shadow"] == "soft"
    assert params["inset"] == "sub"


def test_decide_screenshot_params_editorial_hero_with_texture_uses_monocle():
    image = {"caption": "Code editor hero", "asset_id": "xhs-02"}
    page = {"role": "evidence", "hero": True, "texture": True}
    params = decide_screenshot_params(image, page, mode="editorial", theme="ink-classic")

    assert params["hero"] is True or params["asset_bg"] == "monocle-classic"
    assert params["asset_bg"] == "monocle-classic"
    assert params["shadow"] == "ed"
    assert params["inset"] == "bal"


def test_decide_screenshot_params_swiss_hero_with_ikb_dot():
    image = {"caption": "Product release screenshot", "asset_id": "xhs-02"}
    page = {"role": "evidence", "hero": True, "texture": True}
    params = decide_screenshot_params(image, page, mode="swiss", theme="ikb")

    assert params["asset_bg"] == "ikb-dot"
    assert params["shadow"] in {"none", "soft"}  # 不要 shadow-ed + asset


def test_decide_screenshot_params_mobile_triggers_device_phone():
    image = {"caption": "WeChat app screen", "asset_id": "xhs-02", "alt": "mobile app shot"}
    page = {"role": "evidence"}
    params = decide_screenshot_params(image, page, mode="swiss", theme="ikb")

    assert params["ratio"] == "3x4"
    assert params["device"] == "device-phone"


def test_decide_screenshot_params_wide_for_landscape_dashboard():
    image = {"caption": "wide dashboard", "asset_id": "xhs-02"}
    page = {"role": "evidence"}
    params = decide_screenshot_params(image, page, mode="swiss", theme="ikb")

    assert params["ratio"] in {"16x9", "16x10"}


def test_decide_screenshot_params_grid_kicker_triggers_grid_bg():
    image = {"caption": "Notion dashboard", "asset_id": "xhs-02"}
    page = {"role": "evidence", "kicker": "Data"}
    params = decide_screenshot_params(image, page, mode="swiss", theme="ikb")

    assert params["bg"] == "bg-grid"


def test_decide_screenshot_params_accent_mismatch_omits_asset_bg():
    """theme=lemon 但 page 标 texture=True：仍可走 asset，但只在 accent 匹配时。"""
    image = {"caption": "dashboard", "asset_id": "xhs-02"}
    page = {"role": "evidence", "hero": True, "texture": True}
    params = decide_screenshot_params(image, page, mode="swiss", theme="orange")

    # theme='orange' 不在 swiss accent 映射中，asset_bg 应为空
    assert params["asset_bg"] is None


# -----------------------------------------------------------------------------
# 4. render_screenshot_frame：HTML 渲染
# -----------------------------------------------------------------------------


def test_render_screenshot_frame_emits_frame_shot_with_all_classes():
    image = {
        "src": "assets/images/dashboard.png",
        "caption": "Linear dashboard",
        "asset_id": "xhs-02",
    }
    page = {"role": "evidence"}
    html = render_screenshot_frame(image, page, mode="swiss", theme="ikb")

    assert "frame-shot" in html
    assert "r-16x10" in html
    assert "corners-sq" in html
    assert "shadow-none" in html
    assert "bg-grey-1" in html
    assert "inset-sub" in html
    assert 'src="assets/images/dashboard.png"' in html
    assert "Linear dashboard" in html
    assert "device-" not in html  # 非手机


def test_render_screenshot_frame_mobile_wraps_with_device_phone():
    image = {
        "src": "assets/images/app.png",
        "caption": "WeChat app",
        "asset_id": "xhs-02",
        "alt": "mobile app",
    }
    page = {"role": "evidence"}
    html = render_screenshot_frame(image, page, mode="swiss", theme="ikb")

    assert "device-phone" in html
    assert "r-3x4" in html


def test_render_screenshot_frame_returns_empty_when_no_src():
    image = {"caption": "missing src"}
    page = {"role": "evidence"}
    assert render_screenshot_frame(image, page) == ""


def test_render_screenshot_frame_uses_bg_asset_for_editorial_hero():
    image = {
        "src": "assets/images/code.png",
        "caption": "Code editor hero",
        "asset_id": "xhs-02",
    }
    page = {"role": "evidence", "hero": True, "texture": True}
    html = render_screenshot_frame(image, page, mode="editorial", theme="ink-classic")

    assert "bg-asset-monocle-classic" in html
    assert "shadow-ed" in html
    assert "inset-bal" in html


# -----------------------------------------------------------------------------
# 5. render_image_frame：分发
# -----------------------------------------------------------------------------


def test_render_image_frame_photo_uses_frame_img_with_figcaption():
    image = {
        "src": "assets/images/portrait.jpg",
        "caption": "CEO portrait",
        "alt": "executive",
        "screenshot": False,  # 显式标 False
    }
    page = {"role": "evidence"}
    html = render_image_frame(image, page, mode="editorial", fig_label="FIG. 01", default_ratio="r-4x3")

    assert "frame-img" in html
    assert "frame-shot" not in html
    assert "<figcaption" in html
    assert "FIG. 01" in html
    assert "CEO portrait" in html


def test_render_image_frame_screenshot_uses_frame_shot():
    image = {
        "src": "assets/images/dashboard.png",
        "caption": "Linear dashboard",
        "asset_id": "xhs-02",
        "screenshot": True,  # 显式标 True
    }
    page = {"role": "evidence"}
    html = render_image_frame(
        image, page, mode="swiss", theme="ikb", fig_label="FIG. 01", default_ratio="r-4x3"
    )

    assert "frame-shot" in html
    assert "frame-img" not in html
    assert "r-16x10" in html


def test_render_image_frame_auto_detects_screenshot_from_captions():
    image = {
        "src": "assets/images/x.png",
        "caption": "VSCode editor screenshot",
        "asset_id": "xhs-02",
        # 未显式标 screenshot
    }
    page = {"role": "evidence"}
    html = render_image_frame(
        image, page, mode="swiss", theme="ikb", fig_label="FIG. 01", default_ratio="r-4x3"
    )

    assert "frame-shot" in html
    assert "r-16x10" in html


def test_render_image_frame_auto_detects_photographic_over_screenshot_string():
    image = {
        "src": "assets/images/y.jpg",
        "caption": "screenshot of mountain scenery",
        "asset_id": "xhs-02",
    }
    page = {"role": "evidence"}
    html = render_image_frame(image, page, mode="editorial", fig_label="FIG. 01", default_ratio="r-4x3")

    # 'scenery' 是摄影强提示 → 走 .frame-img
    assert "frame-img" in html
    assert "frame-shot" not in html


def test_render_image_frame_returns_empty_when_no_src():
    image = {"caption": "no src"}
    assert render_image_frame(image, page={"role": "evidence"}, mode="editorial") == ""
