"""
截图四件套（.frame-shot 六参数）路由与渲染。

按上游 `vendor/guizang/references/screenshot-treatment.md` 决策：
- 比例 r-*（r-16x10 / r-4x3 / r-3x4+device-phone 等）
- 圆角 corners-{sq,sm,md}，与 style 锁定
- 阴影 shadow-{none,soft,ed}
- 舞台 bg-{paper,paper-2,grey-1,grid,dot,ink} 或 bg-asset-{*}
- 内边距 inset-{none,sub,bal}
- 可选 .device-browser / .device-phone 包裹

判定启发式由 `detect_screenshot()` 提供。
"""

from __future__ import annotations

from html import escape
from typing import Iterable


# -----------------------------------------------------------------------------
# 1. 判定：是不是 UI 截图
# -----------------------------------------------------------------------------

# 关键词命中：UI / app / dashboard / code / IDE / terminal / browser 抓屏
_SCREENSHOT_HINTS: tuple[str, ...] = (
    "screenshot", "screen-shot", "screen_shot", "screen capture", "screen-capture",
    "ui shot", "ui-shot", "app shot", "app-shot", "app capture", "app screenshot",
    "interface", "dashboard", "panel", "admin", "settings page",
    "code shot", "code-shot", "ide", "editor", "terminal", "console", "cli",
    "browser", "web capture", "web-capture", "desktop capture", "desktop-capture",
    "screenshot.png", "screenshot.jpg", "screenshot.webp",
    "wechat 截图", "截屏", "截图", "界面图", "应用截图",
    "app 内", "app内",
)

# 排除：明显是摄影/插画/3D 渲染的图
_PHOTOGRAPHIC_HINTS: tuple[str, ...] = (
    "人像", "肖像", "自拍", "半身", "全身", "特写", "脸", "手",
    "风景", "街景", "山川", "海边", "山野", "城市", "建筑外观", "外景",
    "食物", "菜品", "摆盘", "美食大片", "菜片",
    "portrait", "selfie", "person", "people", "face", "hand",
    "landscape", "scenery", "cityscape", "outdoor", "exterior",
    "food", "dish", "cuisine", "meal",
    "插画", "矢量", "3d", "3d 渲染", "render",
    "illustration", "vector", "3d render", "3d-render", "cgi",
)


import re


def _word_hits(needles: Iterable[str], haystack: str) -> list[str]:
    """词匹配：ASCII 走 \b 单词边界（避免 'ide' 命中 'evidence'）；非 ASCII 走 contains。"""
    hits: list[str] = []
    for n in needles:
        n_lower = n.lower()
        if n_lower.isascii() and n_lower.replace(" ", "").replace("-", "").isalnum():
            if re.search(rf"\b{re.escape(n_lower)}\b", haystack):
                hits.append(n)
        elif n_lower and n_lower in haystack:
            hits.append(n)
    return hits


def detect_screenshot(image: dict, page: dict | None = None) -> bool:
    """启发式：图（与 page 角色）是否属于 UI 截图。

    命中规则（短路或）：
    - 任何摄影/插画强提示 → False（即使有 screenshot 字符串也以摄影为先）
    - screenshot / ui / app / dashboard / code / terminal 关键词命中 → True
    - 角色 evidence + 摘要里出现 ui/app/code → True
    - asset_id / filename 含 screenshot / ui / app / dashboard / code / ide / browser → True

    使用单词边界匹配，避免 "ide" 误中 "evidence"、"code" 误中 "encode" 等。
    """
    haystack = " ".join(
        str(item or "")
        for item in (
            image.get("caption"),
            image.get("alt"),
            image.get("asset_id"),
            image.get("filename"),
            image.get("source_url"),
            image.get("description"),
            (page or {}).get("role"),
            (page or {}).get("caption"),
            (page or {}).get("kicker"),
        )
    ).lower()

    if not haystack.strip():
        return False

    # 摄影/插画强提示优先 → 不视作截图
    if _word_hits(_PHOTOGRAPHIC_HINTS, haystack):
        return False

    return bool(_word_hits(_SCREENSHOT_HINTS, haystack))


# -----------------------------------------------------------------------------
# 2. 六参数决策
# -----------------------------------------------------------------------------

# 比例：app/web 抓屏 → 16x10；手机抓屏 → 3x4 + device-phone；其他 → 4x3 兜底
_RATIO_DEFAULT = "16x10"
_RATIO_MOBILE = "3x4"
_RATIO_DASHBOARD = "4x3"
_RATIO_WIDE = "16x9"
_RATIO_HERO = "21x9"

# 手机抓屏识别
_MOBILE_HINTS: tuple[str, ...] = (
    "mobile", "phone", "ios", "android", "wechat", "app 内", "app内",
    "手机", "移动", "微信",
)


def _pick_ratio(image: dict, page: dict | None) -> str:
    """ratio 决策（按上游 cheat-sheet 优先级）：
    - hero 标记 → 21x9
    - mobile 关键词（app/ios/android/wechat/手机/微信）→ 3x4
    - 显式 wide 关键词 → 16x9
    - 兜底 16x10（app/web 抓屏默认；上游两个 cheat-sheet 配方都用 16x10）
    """
    haystack = " ".join(
        str(image.get(k, "")) for k in ("caption", "alt", "asset_id", "filename")
    ).lower()
    if (page or {}).get("hero"):
        return _RATIO_HERO
    if _word_hits(_MOBILE_HINTS, haystack):
        return _RATIO_MOBILE
    if _word_hits(("wide", "wide chart", "landscape video"), haystack):
        return _RATIO_WIDE
    return _RATIO_DEFAULT


def _pick_corners(mode: str) -> str:
    # 上游规则：Swiss 默认 sq；Editorial 默认 sm
    return "sq" if mode == "swiss" else "sm"


def _pick_shadow(mode: str, page: dict | None, params: dict) -> str:
    # 上游规则：
    # - Swiss 90% none；grid/dot 舞台可用 soft
    # - Editorial 默认 soft（warm paper-2）；hero 用 ed
    if mode == "swiss":
        if params["bg"] in {"bg-grid", "bg-dot"}:
            return "soft"
        if (page or {}).get("hero"):
            return "none"
        return "none"
    # editorial
    if (page or {}).get("hero"):
        return "ed"
    return "soft"


def _pick_bg(mode: str, theme: str | None, page: dict | None) -> str:
    # 默认舞台：Swiss grey-1；Editorial paper-2
    if mode == "swiss":
        if (page or {}).get("hero"):
            # hero 可以走 asset（在 _pick_asset_bg 内）
            return "bg-grey-1"
        if (page or {}).get("kicker", "").lower() in {"data", "matrix", "engineer"}:
            return "bg-grid"
        return "bg-grey-1"
    # editorial
    if (page or {}).get("hero"):
        return "bg-paper-2"
    return "bg-paper-2"


def _pick_inset(mode: str, page: dict | None) -> str:
    # hero 走 inset-bal 让画面更呼吸；常规 sub；显式 inset-none 在用户给 full chrome 时
    if (page or {}).get("hero"):
        return "bal"
    if (page or {}).get("role") == "evidence":
        return "sub"
    return "sub"


def _pick_asset_bg(mode: str, theme: str | None) -> str | None:
    """是否走 9 张 .bg-asset-* 之一。Swiss 仅在 accent 匹配时走，Editorial 不限。"""
    if mode == "swiss":
        accent = (theme or "").lower()
        mapping = {
            "ikb": "ikb-dot",
            "lemon-yellow": "lemon-grid",
            "lemon": "lemon-grid",
            "lemon-green": "lemon-green-dot",
            "safety-orange": "safety-orange",
        }
        return mapping.get(accent)
    # editorial 5 个全部可用
    return "monocle-classic"


def _wants_texture(page: dict | None) -> bool:
    return bool((page or {}).get("hero") and (page or {}).get("texture"))


def decide_screenshot_params(
    image: dict,
    page: dict | None = None,
    *,
    mode: str = "swiss",
    theme: str | None = None,
) -> dict:
    """返回 6 参数 + 可选 device 包裹 + 可选 asset_bg。

    字段：
    - ratio, corners, shadow, bg, inset, device, asset_bg
    """
    page = page or {}
    ratio = _pick_ratio(image, page)
    params: dict = {
        "ratio": ratio,
        "corners": _pick_corners(mode),
        "bg": _pick_bg(mode, theme, page),
        "inset": _pick_inset(mode, page),
        "hero": bool((page or {}).get("hero")),
        "texture": bool((page or {}).get("texture")),
    }
    params["shadow"] = _pick_shadow(mode, page, params)
    params["device"] = "device-phone" if ratio == _RATIO_MOBILE and mode != "editorial" else None
    params["asset_bg"] = _pick_asset_bg(mode, theme) if _wants_texture(page) else None
    return params


# -----------------------------------------------------------------------------
# 3. 渲染：<div class="device-X"> > <div class="frame-shot X Y Z"> > <img>
# -----------------------------------------------------------------------------

def _class_list(params: dict) -> list[str]:
    classes = ["frame-shot"]
    if params.get("asset_bg"):
        classes.append(f"r-{params['ratio']}")
        classes.append(f"corners-{params['corners']}")
        classes.append(f"shadow-{params['shadow']}")
        classes.append(f"bg-asset-{params['asset_bg']}")
        classes.append(f"inset-{params['inset']}")
    else:
        classes.append(f"r-{params['ratio']}")
        classes.append(f"corners-{params['corners']}")
        classes.append(f"shadow-{params['shadow']}")
        classes.append(params["bg"])
        classes.append(f"inset-{params['inset']}")
    return classes


def render_screenshot_frame(
    image: dict,
    page: dict | None = None,
    *,
    mode: str = "swiss",
    theme: str | None = None,
    min_height: int | None = None,
) -> str:
    """渲染 .device-* > .frame-shot 包裹的截图容器。返回空串当 image 无 src。"""
    src = image.get("src")
    if not src:
        return ""
    page = page or {}
    params = decide_screenshot_params(image, page, mode=mode, theme=theme)
    caption = (
        image.get("caption")
        or image.get("alt")
        or image.get("asset_id")
        or "Source image"
    )
    style_parts: list[str] = []
    if min_height is not None:
        style_parts.append(f"min-height:{min_height}px")
    style = (";".join(style_parts) + ";") if style_parts else ""
    classes = " ".join(_class_list(params))
    inner = (
        f'<div class="{classes}" style="{style}">'
        f'<img src="{escape(str(src))}" alt="{escape(str(caption))}" '
        f'style="object-position:{escape(str(image.get("object_position", "center 50%")))}">'
        f'</div>'
    )
    if params.get("device"):
        return f'<div class="{params["device"]}">{inner}</div>'
    return inner


# -----------------------------------------------------------------------------
# 4. 分发：拍图用 .frame-img，截图用 .frame-shot
# -----------------------------------------------------------------------------

def _image_caption(image: dict, default: str) -> str:
    return (
        image.get("caption")
        or image.get("alt")
        or image.get("asset_id")
        or default
    )


def render_image_frame(
    image: dict,
    page: dict | None = None,
    *,
    mode: str = "swiss",
    theme: str | None = None,
    fig_label: str = "FIG. 01",
    default_ratio: str = "r-4x3",
) -> str:
    """统一图渲染入口。

    - 若 image.screenshot 已显式标注为 True / False → 直接走对应路径
    - 否则用 detect_screenshot() 启发式判定
    - screenshot → render_screenshot_frame
    - 否则 → .frame-img + figcaption（与原 _image_figure 行为一致）
    """
    if not image.get("src"):
        return ""

    explicit = image.get("screenshot")
    if explicit is True:
        is_shot = True
    elif explicit is False:
        is_shot = False
    else:
        is_shot = detect_screenshot(image, page)

    if is_shot:
        return render_screenshot_frame(image, page, mode=mode, theme=theme)

    # 摄影/插画路径：保留原 .frame-img + figcaption 行为
    caption = _image_caption(image, default="Source image")
    return (
        f'<figure class="frame-img {default_ratio}">'
        f'<img src="{escape(str(image.get("src")))}" alt="{escape(caption)}" '
        f'style="object-position:{escape(str(image.get("object_position", "center 50%")))}">'
        f'<figcaption class="img-cap">{escape(fig_label)} · {escape(caption)}</figcaption>'
        f'</figure>'
    )
