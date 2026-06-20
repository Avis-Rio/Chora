"""
主体映射（subject map）决策与生成。

按上游 `vendor/guizang/references/image-overlay.md` Rule 2：
- 主体区（subject zone）：face / focal feature / silhouette edge
- 安全文本区（safe text zone）：above / below / one side / diagonal corner
- object_position 决策（基于主体垂直第三）

默认按 caption/alt/filename 关键词启发式推断；若调用方传入本地图像路径且
`CHORA_DISTRIBUTION_VISION_PROVIDER=gemini`，会先查 vision cache，再调用
Gemini vision 增强主体区与安全区。vision 失败时记录并回退启发式。
"""

from __future__ import annotations

from html import escape
from pathlib import Path
import re
from typing import Iterable


# -----------------------------------------------------------------------------
# 1. 主体类型推断
# -----------------------------------------------------------------------------

SUBJECT_TYPES = {
    "portrait":   {"label": "人像",     "face": True,  "default_focus": "upper-center"},
    "full_body":  {"label": "全身",     "face": True,  "default_focus": "center"},
    "product":    {"label": "产品",     "face": False, "default_focus": "center"},
    "landscape":  {"label": "风景",     "face": False, "default_focus": "horizon-line"},
    "cityscape":  {"label": "城市",     "face": False, "default_focus": "horizon-line"},
    "food":       {"label": "食物",     "face": False, "default_focus": "center"},
    "animal":     {"label": "动物",     "face": True,  "default_focus": "lower-center"},
    "object":     {"label": "静物",     "face": False, "default_focus": "center"},
    "abstract":   {"label": "抽象",     "face": False, "default_focus": "uniform"},
}

SUBJECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "portrait":  ("人像", "肖像", "半身", "脸", "人脸", "自拍", "portrait", "selfie", "person face", "executive", "speaker", "interview", "headshot"),
    "full_body": ("全身", "全身照", "ootd 全身", "full body", "full-body", "全身穿搭", "全身自拍"),
    "product":   ("产品", "device", "产品图", "product", "iphone", "macbook", "laptop", "gadget", "商品", "设备"),
    "landscape": ("山", "海", "森林", "沙漠", "风景", "山川", "海边", "山野", "landscape", "mountain", "ocean", "forest", "desert", "peak", "summit", "outdoor", "野外"),
    "cityscape": ("城市", "街景", "建筑", "city", "cityscape", "urban", "skyline", "夜景", "夜景街景"),
    "food":      ("美食", "食物", "菜品", "摆盘", "food", "dish", "cuisine", "meal"),
    "animal":    ("猫", "狗", "动物", "cat", "dog", "animal", "pet", "鸟类", "bird"),
    "object":    ("静物", "still life", "object", "item"),
    "abstract":  ("插画", "矢量", "3d", "3d 渲染", "render", "illustration", "vector", "cgi"),
}

# Atmospheric / 柔光（light test 通过）
ATMOSPHERIC_HINTS: tuple[str, ...] = (
    "overcast", "fog", "dawn", "dusk", "golden hour", "film soft",
    "understory", "atmospheric", "soft light", "moody",
    "阴天", "晨雾", "黄昏", "金色时刻", "胶片", "晨光", "暮色", "雾", "昏暗", "柔光",
)

# High saturation / 强日光（light test 失败）
HIGH_SATURATION_HINTS: tuple[str, ...] = (
    "noon", "high saturation", "tourist", "stock cheerfulness",
    "正午", "高饱和", "游客照", "强光", "hard light",
)

# Quiet zone 关键词（图中"低细节带"）
QUIET_ZONE_HINTS: tuple[str, ...] = (
    "sky", "fog", "shade", "blurred", "background", "calm water", "plain sky",
    "blurred grass", "out-of-focus", "deep shade",
    "天空", "雾", "阴影", "背景虚化", "远景", "纯色", "uniform",
    "留白", "低细节",
)

# 主体垂直位置关键词（决定 object_position）
VERTICAL_THIRD_HINTS = {
    "upper":  ("upper third", "face top", "head high", "顶部", "上方", "顶三分之一"),
    "middle": ("middle third", "center", "horizon line", "中段", "中间", "中部"),
    "lower":  ("lower third", "ground level", "底部", "下方", "底三分之一", "地面"),
}


def _word_hits(needles: Iterable[str], haystack: str) -> list[str]:
    """词匹配：ASCII 走 \\b 单词边界；非 ASCII 走 contains。"""
    hits: list[str] = []
    for n in needles:
        n_lower = n.lower()
        if n_lower.isascii() and n_lower.replace(" ", "").replace("-", "").isalnum():
            if re.search(rf"\b{re.escape(n_lower)}\b", haystack):
                hits.append(n)
        elif n_lower and n_lower in haystack:
            hits.append(n)
    return hits


def _collect_image_text(image: dict, page: dict | None = None) -> str:
    parts = [
        image.get("caption"),
        image.get("alt"),
        image.get("asset_id"),
        image.get("filename"),
        image.get("description"),
        image.get("provider"),
        (page or {}).get("title"),
        (page or {}).get("kicker"),
        (page or {}).get("caption"),
        (page or {}).get("role"),
    ]
    return " ".join(str(p or "") for p in parts).lower()


def classify_subject(image: dict, page: dict | None = None) -> dict:
    """返回 {type, label, face, default_focus, hit_keyword}。"""
    text = _collect_image_text(image, page)
    if not text.strip():
        return {
            "type": "abstract", "label": "抽象", "face": False,
            "default_focus": "uniform", "hit_keyword": None,
        }
    for subject_type, keywords in SUBJECT_KEYWORDS.items():
        hits = _word_hits(keywords, text)
        if hits:
            spec = SUBJECT_TYPES[subject_type]
            return {
                "type": subject_type,
                "label": spec["label"],
                "face": spec["face"],
                "default_focus": spec["default_focus"],
                "hit_keyword": hits[0],
            }
    return {
        "type": "abstract", "label": "抽象", "face": False,
        "default_focus": "uniform", "hit_keyword": None,
    }


# -----------------------------------------------------------------------------
# 2. Quiet-zone / Light test 判定
# -----------------------------------------------------------------------------

def passes_quiet_zone(image: dict, page: dict | None = None) -> bool:
    """Rule 1 Step 1：图是否有 ≥30% canvas 低细节带（基于 hint 启发式）。

    严格只看 image metadata；page role 不参与判定（page 不会让一张紧人像变出
    quiet zone）。
    """
    text = _collect_image_text(image, None)  # 不看 page
    if not text.strip():
        return False
    subject = classify_subject(image, page)
    if subject["type"] in ("landscape", "cityscape"):
        return True
    if _word_hits(QUIET_ZONE_HINTS, text):
        return True
    return False


def passes_light_test(image: dict, page: dict | None = None) -> bool:
    """Rule 1 Step 1：light test（atmospheric vs high-saturation noon）。"""
    text = _collect_image_text(image, None)
    if not text.strip():
        return False
    if _word_hits(HIGH_SATURATION_HINTS, text):
        return False
    if _word_hits(ATMOSPHERIC_HINTS, text):
        return True
    subject = classify_subject(image, page)
    return subject["type"] in ("landscape", "cityscape", "object")


# -----------------------------------------------------------------------------
# 3. Safe-zone placement（kicker / title / body 位置）
# -----------------------------------------------------------------------------

def pick_safe_zone(subject: dict, page_role: str | None = None) -> str:
    """返回 safe_zone 标签（one-side / above-below / diagonal-tr / diagonal-tl）。

    90% full-bleed：above + below（kicker top, title bottom）。例外：
    - 人像 / 全身（portrait/full_body）：one-side（文字填对面）
    - 风景 / 城市（landscape/cityscape）：above-below
    - 抽象 / 静物：above-below
    """
    t = subject.get("type", "abstract")
    if t in ("portrait", "full_body", "animal"):
        return "one-side"
    return "above-below"


def pick_object_position(subject: dict, vertical_third: str = "middle") -> str:
    """按主体 vertical 第三返回 object-position（与上游 image-overlay.md crop guards 表对齐）。"""
    if vertical_third == "upper":
        return "center 25%"
    if vertical_third == "lower":
        return "center 70%"
    if vertical_third == "horizon":
        return "center 35%"
    if subject.get("type") == "cityscape":
        return "center 35%"  # 城市天际线，略上偏保留 horizon
    return "center 50%"


def _detect_vertical_third(text: str) -> str:
    for third, hints in VERTICAL_THIRD_HINTS.items():
        if _word_hits(hints, text):
            return third
    return "middle"


# -----------------------------------------------------------------------------
# 4. 完整 subject_map 构建
# -----------------------------------------------------------------------------

def _vision_disabled() -> bool:
    """读 env CHORA_DISTRIBUTION_VISION_PROVIDER。"""
    from os import environ
    raw = environ.get("CHORA_DISTRIBUTION_VISION_PROVIDER", "none").strip().lower()
    return raw in {"", "none", "off", "false", "0"}


def _is_image_metadata_rich(image: dict) -> bool:
    """image metadata 是否充分（caption/alt/description 任一非空；asset_id 是技术 ID 不算）。"""
    return any(str(image.get(k) or "").strip() for k in ("caption", "alt", "description"))


def build_subject_map(
    image: dict,
    page: dict | None = None,
    *,
    image_path: str | Path | None = None,
    cache_dir: str | Path | None = None,
) -> dict:
    """从 image + page metadata 推断完整 subject_map。

    增强路径：若 image_path 给定（且 vision 未禁用），先查 vision 缓存 → 调
    `vision_subject_mapper.build_vision_subject_map` → 与启发式合并。

    返回字段（与 recipes.py / page_planner 约定一致）：
    - type: portrait / full_body / product / landscape / cityscape / food / animal / object / abstract
    - label: 中文标签
    - face: bool（人像/动物/全身为 True）
    - focus: 主体焦点位置描述
    - face_position: {x_pct, y_pct}（vision 才有）
    - silhouette_edge: {left_pct, right_pct, top_pct, bottom_pct}
    - quiet_zone_rect: {x_pct, y_pct, width_pct, height_pct}（vision 才有）
    - safe_zone: above-below / one-side / diagonal-tr / diagonal-tl
    - quiet_zone: 文字描述
    - light: 文字描述
    - object_position: center 25% / center 35% / center 50% / center 70%
    - passes_quiet_zone: bool
    - passes_light: bool
    - requires_localized_tint: bool
    - vision_enhanced: bool（vision 读过则为 True）
    - auto_generated: bool（image metadata 缺则 True）
    """
    text = _collect_image_text(image, page)
    subject = classify_subject(image, page)
    safe = pick_safe_zone(subject, (page or {}).get("role"))
    vertical = _detect_vertical_third(text)
    obj_pos = pick_object_position(subject, vertical)
    qz = passes_quiet_zone(image, page)
    lt = passes_light_test(image, page)
    heuristic = {
        "type": subject["type"],
        "label": subject["label"],
        "face": subject["face"],
        "focus": subject["default_focus"],
        "silhouette_edge": "see photo for subject silhouette",
        "safe_zone": safe,
        "quiet_zone": "≥30% canvas low-detail band" if qz else "no clear quiet band — swap or add tint",
        "light": "atmospheric / restrained light" if lt else "high-saturation noon — swap or tint",
        "object_position": obj_pos,
        "passes_quiet_zone": qz,
        "passes_light": lt,
        "requires_localized_tint": (not qz) or (not lt),
        "hit_keyword": subject["hit_keyword"],
        "auto_generated": not _is_image_metadata_rich(image),
    }

    # Vision 增强：若 image_path 存在且 vision 未禁用，调 Gemini vision 读图
    if image_path and not _vision_disabled():
        try:
            from distribution_pipeline.renderers.guizang.vision_subject_mapper import (
                build_vision_subject_map as _build_vision,
                merge_vision_into_subject_map as _merge_vision,
            )
            vision_smap = _build_vision(Path(image_path), cache_dir=Path(cache_dir) if cache_dir else None)
            if vision_smap:
                return _merge_vision(heuristic, vision_smap)
        except Exception as exc:
            # 失败 → 落回启发式（不阻塞主流程）
            print(f"[subject_mapper] vision 增强失败: {type(exc).__name__}: {exc}")

    return heuristic


# -----------------------------------------------------------------------------
# 5. HTML 注释（按上游示例）
# -----------------------------------------------------------------------------

def subject_map_html_comment(subject_map: dict, page_label: str = "hero") -> str:
    """生成 subject map HTML 注释（与上游示例对齐）。"""
    if not subject_map:
        return ""
    return (
        f"<!-- subject map ({page_label}):\n"
        f"     focus: {escape(str(subject_map.get('focus', '')))}\n"
        f"     silhouette: {escape(str(subject_map.get('silhouette_edge', '')))}\n"
        f"     safe text zone: {escape(str(subject_map.get('safe_zone', '')))}\n"
        f"     quiet-zone test: {escape(str(subject_map.get('quiet_zone', '')))}\n"
        f"     light test: {escape(str(subject_map.get('light', '')))}\n"
        f"     object-position: {escape(str(subject_map.get('object_position', '')))}\n"
        f"     thumbnail policy: verify 360px title readability; if needed, use localized image-toned tint only.\n"
        f"-->"
    )
