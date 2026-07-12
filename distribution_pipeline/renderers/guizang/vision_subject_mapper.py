"""
Vision 读图生成 subject_map（替换 `subject_mapper.py` 启发式为真 vision）。

按上游 `references/image-overlay.md` Rule 2：
"Subject zone discovery — multimodal first. Open it with the Read tool and
observe in plain language: 1) face/focal feature 位置 2) silhouette edge
3) largest open / low-detail area"

复用 Chora 已有 Gemini 客户端（与戊项 `generate_cover.py` 同管线，同 key，
同 `config/sources.yaml['api_keys']['gemini']`）。不新增 provider。

环境变量：
- CHORA_DISTRIBUTION_VISION_PROVIDER=gemini（显式启用）/ none（默认）
- CHORA_DISTRIBUTION_VISION_CONCURRENCY=N（默认 1，即同步串行；>1 走低并发）
- CHORA_DISTRIBUTION_VISION_MAX_PER_PACKAGE=4（默认，每图卡组最多 4 张读图）
- CHORA_DISTRIBUTION_VISION_TIMEOUT=60（秒）
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import os
import re
import sys
from pathlib import Path

VISION_CACHE_FILENAME = ".subject_map_cache.json"
VISION_DEFAULT_MAX_PER_PACKAGE = 4
VISION_DEFAULT_CONCURRENCY = 1
VISION_DEFAULT_TIMEOUT = 60
VISION_PROMPT_VERSION = "v1"


# -----------------------------------------------------------------------------
# 1. Prompt 模板
# -----------------------------------------------------------------------------

_VISION_PROMPT = """你是一位排版编辑，负责判断一张图是否适合做"图文卡"封面（3:4 竖图，标题压在图上）。

请按以下 JSON schema 输出观察结果，**严格 JSON，无多余文字**：

{{
  "primary_subject": {{
    "type": "portrait | full_body | product | landscape | cityscape | food | animal | object | abstract | other",
    "label": "中文标签",
    "face_present": true/false,
    "focal_feature": "主体最显眼的特征（人脸 / 手 / 山尖 / 产品 logo / 菜中央 / 屏幕中心）",
    "face_position": {{"x_pct": 0-100, "y_pct": 0-100}},
    "silhouette_edge": {{"left_pct": 0-100, "right_pct": 0-100, "top_pct": 0-100, "bottom_pct": 0-100}}
  }},
  "quiet_zone": {{
    "x_pct": 0-100, "y_pct": 0-100, "width_pct": 0-100, "height_pct": 0-100,
    "passes_quiet_zone_test": true/false,
    "description": "最大低细节带的简短描述（如'lower-left 30% uniform fog'）"
  }},
  "light": {{
    "passes_light_test": true/false,
    "type": "atmospheric | overcast | dawn | dusk | golden_hour | studio | noon | high_saturation | dim | other"
  }},
  "safe_text_zone": "above-below | one-side | diagonal-tl | diagonal-tr | diagonal-bl | diagonal-br | none",
  "object_position": "center 25% | center 35% | center 50% | center 70% | center top",
  "recommendation": {{
    "text_can_overlay": true/false,
    "reason": "一句话说明为何可以/不可以压字"
  }}
}}

判 quiet_zone_test 通过条件：图中存在至少一条 ≥30% canvas 的低细节带（天空、雾、阴影、纯色背景、虚化区）。
判 passes_light_test 通过条件：光线是 atmospheric / overcast / dawn / dusk / golden_hour / studio / dim；高饱和正午强光失败。
判 text_can_overlay：quiet_zone_test 与 light_test 同时通过，且图无大面积文字/水印/截断主体。

只输出 JSON。"""


# -----------------------------------------------------------------------------
# 2. Env 开关
# -----------------------------------------------------------------------------


def vision_disabled() -> bool:
    raw = os.environ.get("CHORA_DISTRIBUTION_VISION_PROVIDER", "none").strip().lower()
    return raw in {"", "none", "off", "false", "0"}


def vision_concurrency() -> int:
    raw = os.environ.get("CHORA_DISTRIBUTION_VISION_CONCURRENCY", str(VISION_DEFAULT_CONCURRENCY))
    try:
        return max(1, int(raw))
    except ValueError:
        return VISION_DEFAULT_CONCURRENCY


def vision_max_per_package() -> int:
    raw = os.environ.get("CHORA_DISTRIBUTION_VISION_MAX_PER_PACKAGE", str(VISION_DEFAULT_MAX_PER_PACKAGE))
    try:
        return max(0, int(raw))
    except ValueError:
        return VISION_DEFAULT_MAX_PER_PACKAGE


def vision_timeout() -> int:
    raw = os.environ.get("CHORA_DISTRIBUTION_VISION_TIMEOUT", str(VISION_DEFAULT_TIMEOUT))
    try:
        return max(5, int(raw))
    except ValueError:
        return VISION_DEFAULT_TIMEOUT


# -----------------------------------------------------------------------------
# 3. Gemini REST 调用（与戊项 generate_cover.py 同管线，不依赖 generate_cover）
# -----------------------------------------------------------------------------


def _load_gemini_config(config_path: Path | None = None) -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from config_loader import load_sources_config

    if config_path is None:
        config_path = repo_root / "config" / "sources.yaml"

    config = load_sources_config(str(config_path))
    if config is None:
        raise RuntimeError(f"未找到 {config_path}；vision 需 Gemini key 与 base_url")
    api = config.get("api_keys", {}).get("gemini", {})
    if not api.get("api_key") or not api.get("base_url"):
        raise RuntimeError("config/sources.yaml 中 api_keys.gemini 缺 api_key 或 base_url")
    return api


def _encode_image(image_path: Path) -> tuple[str, str]:
    """返回 (mime_type, base64_data)。"""
    suffix = image_path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".heic": "image/heic",
    }.get(suffix, "image/png")
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return mime, data


def _post_gemini_request(base_url: str, api_key: str, payload: dict):
    import requests  # type: ignore[import-not-found]

    return requests.post(
        base_url,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=vision_timeout(),
    )


def call_gemini_vision(image_path: Path, prompt: str | None = None) -> str | None:
    """调 Gemini REST（generateContent）做 vision 读图；返回 text（应为 JSON）。"""
    api = _load_gemini_config()
    base_url = api["base_url"]
    api_key = api["api_key"]
    mime, b64 = _encode_image(image_path)
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt or _VISION_PROMPT},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }
    try:
        response = _post_gemini_request(base_url, api_key, payload)
    except Exception as exc:
        print(f"[vision_subject_mapper] Gemini vision 网络异常: {exc}")
        return None
    if response.status_code != 200:
        print(f"[vision_subject_mapper] Gemini vision 非 200: {response.status_code} {response.text[:200]}")
        return None
    try:
        result = response.json()
    except json.JSONDecodeError:
        return None
    # Gemini 原生：candidates[0].content.parts[0].text
    candidates = result.get("candidates") or []
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        text = part.get("text")
        if text:
            return text
    return None


# -----------------------------------------------------------------------------
# 4. JSON 解析与校验
# -----------------------------------------------------------------------------


def _extract_json_blob(text: str) -> dict | None:
    """从 Gemini 输出中提取 JSON（容忍 ```json 围栏）。"""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    blob = fence.group(1) if fence else text.strip()
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        # 容错：取第一个 { ... } 段
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _clamp_pct(value, default: float = 50.0) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return default


def _normalize_vision_output(raw: dict) -> dict:
    """从 Gemini 输出标准化为 subject_map 字段。"""
    raw = raw or {}
    subj = raw.get("primary_subject") or {}
    quiet = raw.get("quiet_zone") or {}
    light = raw.get("light") or {}
    face = subj.get("face_position") or {}
    edge = subj.get("silhouette_edge") or {}
    safe_zone = raw.get("safe_text_zone") or "above-below"
    obj_pos = raw.get("object_position") or "center 50%"
    if safe_zone not in {
        "above-below",
        "one-side",
        "diagonal-tl",
        "diagonal-tr",
        "diagonal-bl",
        "diagonal-br",
        "none",
    }:
        safe_zone = "above-below"
    if obj_pos not in {"center 25%", "center 35%", "center 50%", "center 70%", "center top"}:
        obj_pos = "center 50%"
    return {
        "vision_present": True,
        "type": subj.get("type") or "abstract",
        "label": subj.get("label") or "抽象",
        "face": bool(subj.get("face_present")),
        "focus": subj.get("focal_feature") or "primary subject",
        "face_position": {
            "x_pct": _clamp_pct(face.get("x_pct"), 50.0),
            "y_pct": _clamp_pct(face.get("y_pct"), 50.0),
        },
        "silhouette_edge": {
            "left_pct": _clamp_pct(edge.get("left_pct"), 0.0),
            "right_pct": _clamp_pct(edge.get("right_pct"), 100.0),
            "top_pct": _clamp_pct(edge.get("top_pct"), 0.0),
            "bottom_pct": _clamp_pct(edge.get("bottom_pct"), 100.0),
        },
        "safe_zone": safe_zone,
        "quiet_zone": quiet.get("description")
        or ("≥30% canvas low-detail band" if quiet.get("passes_quiet_zone_test") else "no clear quiet band"),
        "quiet_zone_rect": {
            "x_pct": _clamp_pct(quiet.get("x_pct"), 0.0),
            "y_pct": _clamp_pct(quiet.get("y_pct"), 50.0),
            "width_pct": _clamp_pct(quiet.get("width_pct"), 30.0),
            "height_pct": _clamp_pct(quiet.get("height_pct"), 30.0),
        },
        "light": light.get("type")
        or ("atmospheric / restrained light" if light.get("passes_light_test") else "high-saturation noon"),
        "object_position": obj_pos,
        "passes_quiet_zone": bool(quiet.get("passes_quiet_zone_test")),
        "passes_light": bool(light.get("passes_light_test")),
        "requires_localized_tint": not (
            bool(quiet.get("passes_quiet_zone_test")) and bool(light.get("passes_light_test"))
        ),
        "text_can_overlay": bool((raw.get("recommendation") or {}).get("text_can_overlay")),
        "vision_reason": (raw.get("recommendation") or {}).get("reason", ""),
    }


# -----------------------------------------------------------------------------
# 5. 缓存
# -----------------------------------------------------------------------------


def _image_hash(image_path: Path, prompt_version: str = VISION_PROMPT_VERSION) -> str:
    """基于文件字节 + 大小 + 提示版本哈希（避免大文件 base64 进 key）。"""
    h = hashlib.sha1()
    h.update(str(image_path).encode("utf-8"))
    h.update(prompt_version.encode("utf-8"))
    try:
        stat = image_path.stat()
        h.update(str(stat.st_size).encode("utf-8"))
        h.update(str(int(stat.st_mtime)).encode("utf-8"))
        # 抽样 4 KB 做内容指纹（避免读 10 MB 图）
        with image_path.open("rb") as f:
            h.update(f.read(4096))
    except OSError:
        pass
    return h.hexdigest()[:16]


def _load_vision_cache(cache_dir: Path) -> dict:
    cache_path = cache_dir / VISION_CACHE_FILENAME
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_vision_cache(cache_dir: Path, cache: dict) -> None:
    cache_path = cache_dir / VISION_CACHE_FILENAME
    try:
        cache_path.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def vision_cache_lookup(cache_dir: Path, image_path: Path) -> dict | None:
    h = _image_hash(image_path)
    cache = _load_vision_cache(cache_dir)
    entry = cache.get(h)
    if not entry or not entry.get("vision_present"):
        return None
    entry["_cache_hit"] = True
    return entry


def vision_cache_remember(cache_dir: Path, image_path: Path, vision_smap: dict) -> None:
    h = _image_hash(image_path)
    cache = _load_vision_cache(cache_dir)
    cache[h] = vision_smap
    _save_vision_cache(cache_dir, cache)


# -----------------------------------------------------------------------------
# 6. 主入口
# -----------------------------------------------------------------------------


def build_vision_subject_map(image_path: Path, cache_dir: Path | None = None) -> dict | None:
    """vision 读图返回 subject_map（normalized）。失败返回 None。

    失败回退路径：调用方应回退到 `subject_mapper.build_subject_map`（启发式）。
    """
    image_path = Path(image_path)
    if not image_path.exists():
        return None
    cache_dir = cache_dir or image_path.parent

    cached = vision_cache_lookup(cache_dir, image_path)
    if cached is not None:
        return cached
    if vision_disabled():
        return None

    text = call_gemini_vision(image_path)
    if not text:
        return None
    raw = _extract_json_blob(text)
    if not raw:
        return None
    smap = _normalize_vision_output(raw)
    vision_cache_remember(cache_dir, image_path, smap)
    return smap


# -----------------------------------------------------------------------------
# 7. 合并 vision + 启发式
# -----------------------------------------------------------------------------


def merge_vision_into_subject_map(heuristic: dict, vision: dict) -> dict:
    """vision 覆盖坐标字段，heuristic 保留 type/label/face 标签。

    合并原则：
    - vision_present 时，坐标字段（face_position / silhouette_edge / quiet_zone_rect /
      object_position）从 vision 取
    - safe_zone 优先 vision（但若 vision 给 "none" 落回启发式 safe_zone）
    - 文字描述（focus / quiet_zone / light）vision 优先
    - 其它保留 heuristic
    """
    if not vision or not vision.get("vision_present"):
        return heuristic
    merged = dict(heuristic)  # copy
    # vision 类型 / 标签
    if vision.get("type") and vision["type"] != "abstract":
        merged["type"] = vision["type"]
    if vision.get("label") and vision["label"] != "抽象":
        merged["label"] = vision["label"]
    merged["face"] = bool(vision.get("face", heuristic.get("face", False)))
    # 坐标字段
    if vision.get("face_position"):
        merged["face_position"] = vision["face_position"]
    if vision.get("silhouette_edge"):
        merged["silhouette_edge"] = vision["silhouette_edge"]
    if vision.get("quiet_zone_rect"):
        merged["quiet_zone_rect"] = vision["quiet_zone_rect"]
    # safe_zone：vision 优先（但 "none" 落回启发式）
    v_safe = vision.get("safe_zone")
    if v_safe and v_safe != "none":
        merged["safe_zone"] = v_safe
    # object_position
    if vision.get("object_position"):
        merged["object_position"] = vision["object_position"]
    # 文字描述
    if vision.get("focus"):
        merged["focus"] = vision["focus"]
    if vision.get("quiet_zone"):
        merged["quiet_zone"] = vision["quiet_zone"]
    if vision.get("light"):
        merged["light"] = vision["light"]
    # 测试结果
    merged["passes_quiet_zone"] = bool(vision.get("passes_quiet_zone", heuristic.get("passes_quiet_zone")))
    merged["passes_light"] = bool(vision.get("passes_light", heuristic.get("passes_light")))
    merged["requires_localized_tint"] = not (merged["passes_quiet_zone"] and merged["passes_light"])
    # 标记
    merged["vision_enhanced"] = True
    merged["text_can_overlay"] = bool(vision.get("text_can_overlay", False))
    merged["vision_reason"] = vision.get("vision_reason", "")
    merged["auto_generated"] = False  # 真 vision 看过
    return merged


# -----------------------------------------------------------------------------
# 8. 配额与并发
# -----------------------------------------------------------------------------


def call_vision_for_pages(
    image_paths: list[Path],
    cache_dir: Path,
    *,
    max_per_package: int | None = None,
    concurrency: int | None = None,
) -> list[tuple[Path, dict | None]]:
    """批量调 vision，遵守配额与并发。

    返回 [(image_path, vision_smap_or_None), ...] 顺序与输入一致。
    """
    if vision_disabled():
        return [(p, None) for p in image_paths]
    max_n = max_per_package if max_per_package is not None else vision_max_per_package()
    conc = max(1, concurrency or vision_concurrency())
    selected = image_paths[:max_n]
    skipped = image_paths[max_n:]
    results: list[tuple[Path, dict | None]] = []

    def _one(path: Path) -> tuple[Path, dict | None]:
        try:
            return path, build_vision_subject_map(path, cache_dir=cache_dir)
        except Exception as exc:
            print(f"[vision_subject_mapper] {path.name} vision 失败: {type(exc).__name__}: {exc}")
            return path, None

    if conc == 1:
        for path in selected:
            results.append(_one(path))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=conc) as ex:
            futures = [ex.submit(_one, path) for path in selected]
            for fut in concurrent.futures.as_completed(futures):
                results.append(fut.result())
    for path in skipped:
        results.append((path, None))
    return results
