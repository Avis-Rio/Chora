"""
AI 生图网关：gate 决策 + 缓存 + 调 Chora 已有的 `generate_cover.py`（Gemini）。

按上游 `references/image-overlay.md` Rule 1 Step 1：quiet-zone test / light test
不通过的图应当换图（不要加 mask），所以 C 通道兜底是合理路径。
按上游 `references/production-workflow.md` "Generated Images" 章节：
- 仅在 1-2 张卡上用，**克制**
- 图中不放文字、页码、logo、fake UI（除非显式要求）
- prompt 短而角色化

按上游 `references/content-planning.md` 提示词模板（Swiss style 示例）：
"Swiss style conceptual product image, Android home screen widgets generated
by natural language, clean off-white background, one IKB blue accent, no text,
no logo, 3:4."
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterable


# -----------------------------------------------------------------------------
# 1. Gate 决策：何时调 AI 生图
# -----------------------------------------------------------------------------

# C 通道角色：哪些 role 走 AI 兜底
AI_COVERED_ROLES: frozenset[str] = frozenset({"evidence", "cover_hero", "cover"})


def should_generate_via_ai(
    request: dict,
    selected_assets: list[dict],
    *,
    ai_disabled: bool = False,
) -> bool:
    """决定是否对 request 调 AI 生图。

    触发条件（同时满足）：
    1. 全局 ai_disabled=False（env CHORA_DISTRIBUTION_AI_IMAGE=false 关闭）
    2. request.role ∈ AI_COVERED_ROLES
    3. request 还没被任何 available 候选满足（target_pages 都不在 available_pages）
    4. 上游 "AI 生图克制地用"——每图卡组最多 2 次 AI 生图（由 caller 维护配额）
    """
    if ai_disabled:
        return False
    role = request.get("role", "")
    if role not in AI_COVERED_ROLES:
        return False
    target_pages = set(request.get("target_pages", []) or [])
    if not target_pages:
        return False
    for asset in selected_assets:
        if asset.get("status") != "available":
            continue
        pages = set(asset.get("target_pages", []) or [])
        if pages & target_pages:
            return False
    return True


# -----------------------------------------------------------------------------
# 2. 缓存：内容哈希 → 已生成图（避免重复）
# -----------------------------------------------------------------------------

CACHE_FILENAME = ".ai_image_cache.json"


def _content_hash(*parts: str) -> str:
    """对 (role, query, target_pages, theme) 计算稳定哈希。"""
    blob = "::".join(str(p or "") for p in parts)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def _load_cache(cache_dir: Path) -> dict:
    cache_path = cache_dir / CACHE_FILENAME
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_cache(cache_dir: Path, cache: dict) -> None:
    cache_path = cache_dir / CACHE_FILENAME
    try:
        cache_path.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass  # 缓存失败不阻塞主流程


def lookup_cache(
    cache_dir: Path,
    *,
    role: str,
    query: str,
    target_pages: list[str],
    theme: str | None = None,
) -> dict | None:
    """缓存命中则返回 asset 字典；否则 None。"""
    h = _content_hash(role, query, ",".join(sorted(target_pages)), theme or "")
    cache = _load_cache(cache_dir)
    entry = cache.get(h)
    if not entry:
        return None
    filename = entry.get("filename")
    if not filename:
        return None
    asset_path = cache_dir / filename
    if not asset_path.exists():
        return None
    return {
        "asset_id": entry.get("asset_id", h),
        "provider": "chora-ai-generated",
        "source_type": "ai_generated",
        "status": "available",
        "filename": filename,
        "render_path": f"assets/images/{filename}",
        "target_pages": target_pages,
        "role": role,
        "caption": query,
        "object_position": "center 50%",
        "license_status": "generated-by-chora",
        "preferred_recipe": "",
        "cache_hit": True,
    }


def remember_in_cache(
    cache_dir: Path,
    *,
    role: str,
    query: str,
    target_pages: list[str],
    theme: str | None,
    asset: dict,
) -> None:
    """把新生成的 asset 写入缓存。"""
    h = _content_hash(role, query, ",".join(sorted(target_pages)), theme or "")
    cache = _load_cache(cache_dir)
    cache[h] = {
        "asset_id": asset.get("asset_id", h),
        "filename": asset.get("filename", ""),
    }
    _save_cache(cache_dir, cache)


# -----------------------------------------------------------------------------
# 3. Prompt 构建（按上游 content-planning.md 风格）
# -----------------------------------------------------------------------------

# 11 类（与乙项 category_router 一致）的 AI 生图 prompt 提示
CATEGORY_PROMPTS: dict[str, str] = {
    "travel":       "Editorial travel photo, atmospheric light, warm tones, no text, no logo, 3:4",
    "workplace":    "Swiss style conceptual workplace image, clean off-white background, one IKB blue accent, no text, no logo, 3:4",
    "game":         "Atmospheric game key art, dark moody palette, cinematic lighting, no text, no logo, 3:4",
    "film":         "Cinematic film still, desaturated color, atmospheric depth, no text, no logo, 3:4",
    "food":         "Editorial food photography, warm natural light, restrained composition, no text, no logo, 3:4",
    "makeup":       "Product texture close-up, soft studio light, neutral palette, no text, no logo, 3:4",
    "fitness":      "Swiss style data visualization, strong contrast, IKB blue accent, no text, no logo, 3:4",
    "home":         "Editorial interior, soft natural light, warm wood tones, no text, no logo, 3:4",
    "fashion":      "Editorial fashion detail, soft studio light, restrained palette, no text, no logo, 3:4",
    "emotion":      "Atmospheric essay illustration, soft mist, contemplative mood, no text, no logo, 3:4",
    "recommend":    "Swiss style product matrix, clean grid, one accent color, no text, no logo, 3:4",
}


def build_prompt(query: str, role: str, category: str | None = None, theme: str | None = None) -> str:
    """按上游 `content-planning.md` 模板构建 prompt。"""
    base = CATEGORY_PROMPTS.get(category or "", "Editorial concept image, no text, no logo, 3:4")
    if role == "cover_hero":
        base += ", hero composition, generous negative space"
    if theme:
        base += f", {theme} palette"
    return f"{base}. Subject: {query.strip()}"


# -----------------------------------------------------------------------------
# 4. 调 generate_cover.py（不重写 Gemini client，仅 wrapper）
# -----------------------------------------------------------------------------

def _import_generate_cover():
    """动态 import 项目根的 `generate_cover.py`（不在 distribution_pipeline 路径下）。"""
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        import generate_cover  # type: ignore[import-not-found]
        return generate_cover
    except ImportError as exc:
        raise RuntimeError(
            f"无法 import generate_cover.py（位于 {repo_root}）：{exc}。"
            "戊项复用 Chora 已有 Gemini 客户端，无需新增 API key。"
        ) from exc


def generate_ai_asset(
    *,
    request: dict,
    images_dir: Path,
    category: str | None = None,
    theme: str | None = None,
    prefer_png: bool = True,
) -> dict:
    """调 generate_cover.generate_cover() 出一张 AI 图。

    返回 asset dict（与 image_assets.py 的 selected_assets 兼容）。
    """
    images_dir = Path(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)
    role = request.get("role", "evidence")
    query = request.get("query", "concept image")
    target_pages = request.get("target_pages", [])
    prompt = build_prompt(query, role, category=category, theme=theme)
    ext = "png" if prefer_png else "jpg"
    asset_id = request.get("asset_id") or f"ai-{_content_hash(role, query, ','.join(sorted(target_pages)), theme or '')}"
    filename = f"{asset_id}.{ext}"
    output_path = images_dir / filename

    generate_cover = _import_generate_cover()
    success = generate_cover.generate_cover(
        prompt,
        str(output_path),
        title=request.get("title") or query,
    )
    if not success or not output_path.exists():
        return {
            "asset_id": asset_id,
            "provider": "chora-ai-generated",
            "source_type": "ai_generated",
            "status": "generation_failed",
            "filename": filename,
            "render_path": f"assets/images/{filename}",
            "target_pages": target_pages,
            "role": role,
            "caption": query,
            "object_position": "center 50%",
            "license_status": "generated-by-chora",
            "preferred_recipe": "",
            "prompt": prompt,
        }
    return {
        "asset_id": asset_id,
        "provider": "chora-ai-generated",
        "source_type": "ai_generated",
        "status": "available",
        "filename": filename,
        "render_path": f"assets/images/{filename}",
        "target_pages": target_pages,
        "role": role,
        "caption": query,
        "object_position": "center 50%",
        "license_status": "generated-by-chora",
        "preferred_recipe": "",
        "prompt": prompt,
    }


# -----------------------------------------------------------------------------
# 5. 配额（按上游 "AI 生图克制地用"：每图卡组最多 2 次）
# -----------------------------------------------------------------------------

AI_MAX_PER_PACKAGE = 2


def is_ai_disabled() -> bool:
    """从 env 读 CHORA_DISTRIBUTION_AI_IMAGE，false/0/否/不 → 关闭。"""
    raw = os.environ.get("CHORA_DISTRIBUTION_AI_IMAGE", "true")
    return str(raw).strip().lower() in {"0", "false", "no", "off", "否", "不"}
