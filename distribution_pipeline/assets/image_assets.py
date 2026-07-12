from __future__ import annotations

import copy
import json
import re
from html import escape
from pathlib import Path
from urllib.parse import quote_plus

from distribution_pipeline.assets.ai_image.gateway import (
    AI_MAX_PER_PACKAGE,
    is_ai_disabled,
    lookup_cache,
    remember_in_cache,
    should_generate_via_ai,
)
from distribution_pipeline.assets.downloader import download_candidate, inspect_image_bytes
from distribution_pipeline.assets.providers import default_fetch_json, discover_image_candidates

PROVIDER_NOTES = {
    "pexels": "支持中文搜索，适合大众场景与本地化生活方式图片。",
    "unsplash": "摄影质感强，适合人物、空间、生活方式与科技氛围图。",
    "wallhaven": "适合游戏、摄影、壁纸类视觉，版权状态需人工判断。",
    "flickr_cc": "适合纪实感图片，默认使用 Creative Commons 过滤链接。",
}

COVER_NAMES = ("cover.jpg", "cover.jpeg", "cover.png", "cover.webp")
SEMANTIC_QUERY_RULES = [
    (("孤独的历史性转变", "修道士", "诗人", "牛顿", "狄金森"), "person writing alone window"),
    (("孤独与孤寂", "渴望连接", "充实状态"), "solitary person open landscape"),
    (("being alone", "solitude", "孤独", "孤寂", "独处"), "person alone by window"),
    (("回避", "焦虑", "杏仁核", "卧室", "不出门"), "person alone bedroom window"),
    (("第三空间", "公共空间", "咖啡馆", "公园", "图书馆"), "quiet city cafe library"),
    (
        ("外在动机", "身份", "表演", "点赞", "反应", "社交媒体", "不发布"),
        "person mirror smartphone social media",
    ),
    (("沉默", "自主权", "记录", "测量", "变现"), "person alone window silhouette"),
    (("蛰居", "hikikomori"), "person alone bedroom"),
    (("grow an audience", "followers", "audience", "粉丝", "受众"), "social media content creator"),
    (("初学者", "新手", "专注", "选择过多", "分散注意力"), "focused creator desk"),
    (("互惠", "介绍", "反馈", "关系", "networking"), "creative networking coffee meeting"),
    (("算法", "平台", "流量"), "social media analytics dashboard"),
    (("原创", "创作", "内容"), "creator writing notebook"),
    (("失败", "技能", "模式识别"), "creative learning notebook"),
    (("视觉", "vision", "VLM", "图像", "理解模型"), "computer vision lab"),
    (("Gemini", "DeepMind", "Google", "谷歌"), "AI research lab"),
    (("合并", "团队", "co-lead", "组织", "优先级", "deadline"), "research team strategy meeting"),
    (("数据", "筛选", "清洗", "合成", "语料"), "data center machine learning"),
    (("Transformer", "预训练", "OpenAI", "模型"), "machine learning research lab"),
    (("成本", "Token", "算力", "GPU"), "AI compute data center"),
]


def _has_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def _clean_query(text: str, fallback: str = "editorial technology photography") -> str:
    clean = re.sub(r"https?://\S+", " ", str(text or ""))
    clean = re.sub(r"[^\w\u4e00-\u9fff\s-]+", " ", clean)
    clean = " ".join(clean.split())
    return clean[:80] if clean else fallback


def _asset_slug(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fa5-]+", "-", str(text or "")).strip("-").lower()
    return slug[:80] or "visual"


def _semantic_query(text: str, fallback: str) -> str:
    haystack = str(text or "")
    for needles, query in SEMANTIC_QUERY_RULES:
        if any(needle.lower() in haystack.lower() for needle in needles):
            return query
    return fallback


def _provider_search_urls(query: str) -> dict[str, str]:
    encoded = quote_plus(query)
    pexels_path = "zh-cn/search" if _has_cjk(query) else "search"
    return {
        "pexels": f"https://www.pexels.com/{pexels_path}/{encoded}/",
        "unsplash": f"https://unsplash.com/s/photos/{encoded}",
        "wallhaven": f"https://wallhaven.cc/search?q={encoded}",
        "flickr_cc": f"https://www.flickr.com/search/?text={encoded}&license=2%2C3%2C4%2C5%2C6%2C9",
    }


def _detect_local_cover(content_dir: Path) -> dict | None:
    for name in COVER_NAMES:
        path = content_dir / name
        if path.exists():
            return {
                "asset_id": "source-cover",
                "role": "hero",
                "source_type": "local",
                "status": "available",
                "source_path": str(path),
                "target_pages": ["xhs-01"],
                "caption": "Source cover",
                "license_status": "source-provided",
                "object_position": "center 50%",
            }
    return None


def _query_for_source(source: dict, visual_system: dict) -> str:
    title = source.get("title", "")
    tags = " ".join(source.get("tags", []))
    motifs = " ".join(visual_system.get("visual_motifs", [])[:2])
    semantic = _semantic_query(f"{title} {tags} {motifs}", "")
    if semantic:
        return semantic
    if {"Technology", "Economics"} & set(source.get("tags", [])):
        return _clean_query(f"{title} AI research lab computer vision")
    return _clean_query(f"{title} {tags} {motifs}")


def _query_for_insight(insight: dict, brief: dict | None) -> str:
    title = insight.get("title", "")
    one_liner = insight.get("one_liner") or insight.get("summary", "")
    focal = ""
    if brief:
        focal = brief.get("composition", {}).get("focal_point", "") or brief.get("visual_metaphor", "")
    text = f"{title} {one_liner} {focal}"
    semantic = _semantic_query(text, "")
    if semantic:
        return semantic
    return _clean_query(text, fallback="editorial documentary detail")


def _request(
    asset_id: str,
    role: str,
    target_page: str,
    query: str,
    preferred_recipe: str,
    target_insight_index: int | None = None,
) -> dict:
    providers = ["pexels", "unsplash", "wallhaven", "flickr_cc"]
    return {
        "asset_id": asset_id,
        "role": role,
        "source_type": "web",
        "status": "planned",
        "query": query,
        "providers": providers,
        "search_urls": _provider_search_urls(query),
        "target_pages": [target_page],
        "target_insight_index": target_insight_index,
        "preferred_recipe": preferred_recipe,
        "license_status": "unverified",
        "notes": "待人工或后续下载器选择图片；使用前需确认版权与主体裁切。",
    }


VISUAL_PRIORITY_RULES = [
    ("第三空间", "公共空间", "咖啡馆", "公园", "图书馆"),
    ("外在动机", "身份", "表演", "点赞", "社交媒体", "不发布"),
    ("孤独与孤寂", "渴望连接", "充实状态"),
    ("沉默", "自主权", "记录", "测量", "变现"),
]


def _add_offset(offsets: list[int], offset: int, insight_count: int) -> None:
    if 0 <= offset < insight_count and offset not in offsets:
        offsets.append(offset)


def _priority_evidence_offsets(insights: list[dict], max_evidence: int) -> list[int]:
    offsets = []
    insight_count = len(insights)
    if insight_count:
        offsets.append(0)
    for needles in VISUAL_PRIORITY_RULES:
        for offset, insight in enumerate(insights):
            text = f"{insight.get('title', '')} {insight.get('body', '')} {insight.get('one_liner', '')}"
            if any(needle in text for needle in needles):
                _add_offset(offsets, offset, insight_count)
                break
        if len(offsets) >= max_evidence:
            break
    return offsets[:max_evidence]


def _evidence_page_offsets(
    insight_count: int, max_evidence: int, insights: list[dict] | None = None
) -> list[int]:
    if insight_count <= 0 or max_evidence <= 0:
        return []
    offsets = _priority_evidence_offsets(insights or [], max_evidence) if insights else []
    preferred = [0, 4, 6, 8, 9]
    for offset in preferred:
        _add_offset(offsets, offset, insight_count)
        if len(offsets) >= max_evidence:
            return offsets[:max_evidence]
    next_offset = 1
    while len(offsets) < max_evidence and next_offset < insight_count:
        _add_offset(offsets, next_offset, insight_count)
        next_offset += 1
    return offsets[:max_evidence]


def build_image_asset_plan(
    source: dict,
    insights: list[dict],
    visual_briefs: list[dict],
    visual_system: dict,
    content_dir: Path,
    max_requests: int = 5,
) -> dict:
    content_dir = Path(content_dir)
    local_assets = []
    cover = _detect_local_cover(content_dir)
    if cover:
        local_assets.append(cover)

    requests = [
        _request(
            asset_id="xhs-01-hero-alt",
            role="hero",
            target_page="xhs-01",
            query=_query_for_source(source, visual_system),
            preferred_recipe="M01",
        )
    ]
    briefs_by_index = {brief.get("insight_index"): brief for brief in visual_briefs}
    evidence_offsets = _evidence_page_offsets(len(insights), max_requests - 1, insights)
    for insight_offset in evidence_offsets:
        insight = insights[insight_offset]
        page_number = insight_offset + 2
        brief = briefs_by_index.get(insight.get("index"))
        requests.append(
            _request(
                asset_id=f"xhs-{page_number:02d}-evidence",
                role="evidence",
                target_page=f"xhs-{page_number:02d}",
                query=_query_for_insight(insight, brief),
                preferred_recipe="M10",
                target_insight_index=insight.get("index"),
            )
        )

    return {
        "version": 1,
        "status": "planned",
        "policy": "external image candidates are unverified until the user approves source and attribution",
        "providers": PROVIDER_NOTES,
        "local_assets": local_assets,
        "requests": requests[:max_requests],
    }


def _copy_local_asset(asset: dict, images_dir: Path) -> dict:
    source_path = Path(asset.get("source_path", ""))
    if not source_path.exists():
        copied = dict(asset)
        copied["status"] = "missing"
        return copied
    data = source_path.read_bytes()
    inspection = inspect_image_bytes(data)
    if not inspection.get("width") or not inspection.get("height"):
        copied = dict(asset)
        copied.update(
            inspection,
            status="rejected",
            reason="invalid local image bytes",
        )
        return copied
    suffix = source_path.suffix.lower() or ".jpg"
    filename = f"{asset.get('asset_id', source_path.stem)}{suffix}"
    target = images_dir / filename
    images_dir.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    copied = dict(asset)
    copied.update(inspection)
    copied["filename"] = filename
    copied["render_path"] = f"assets/images/{filename}"
    return copied


def _candidate_identity(candidate: dict) -> str:
    return str(
        candidate.get("source_url") or candidate.get("image_url") or candidate.get("candidate_id") or ""
    )


def _select_candidate(request: dict, used_sources: set[str] | None = None) -> dict | None:
    candidates = request.get("candidates", [])
    if not candidates:
        return None
    used_sources = used_sources or set()
    selected_id = request.get("selected_candidate_id")
    if selected_id:
        for candidate in candidates:
            if (
                candidate.get("candidate_id") == selected_id
                and _candidate_identity(candidate) not in used_sources
            ):
                return candidate
    for candidate in candidates:
        if _candidate_identity(candidate) not in used_sources:
            return candidate
    return candidates[0]


def enrich_image_candidates(
    plan: dict,
    *,
    fetch_json=None,
    max_candidates: int = 3,
) -> dict:
    enriched = copy.deepcopy(plan)
    next_requests = []
    for request in enriched.get("requests", []):
        next_request = dict(request)
        provider_errors = []
        try:
            candidates = discover_image_candidates(
                next_request,
                fetch_json=fetch_json,
                max_candidates=max_candidates,
                error_sink=provider_errors,
            )
        except Exception as exc:  # pragma: no cover - exact network errors vary by platform
            candidates = next_request.get("candidates", [])
            next_request["candidate_error"] = str(exc)
        if provider_errors:
            next_request["candidate_errors"] = provider_errors
        if candidates:
            next_request["candidates"] = candidates
            next_request["status"] = "candidates"
        next_requests.append(next_request)
    enriched["requests"] = next_requests
    if any(request.get("candidates") for request in next_requests):
        enriched["status"] = "candidates"
    return enriched


def download_selected_assets(
    plan: dict,
    assets_dir: Path,
    *,
    fetch_bytes=None,
    min_width: int = 640,
    min_height: int = 480,
) -> dict:
    downloaded = copy.deepcopy(plan)
    images_dir = Path(assets_dir) / "images"
    selected_assets = []
    next_requests = []
    used_sources: set[str] = set()
    for request in downloaded.get("requests", []):
        next_request = dict(request)
        candidate = _select_candidate(next_request, used_sources)
        if not candidate:
            next_requests.append(next_request)
            continue
        selected = download_candidate(
            next_request,
            candidate,
            images_dir,
            fetch_bytes=fetch_bytes,
            min_width=min_width,
            min_height=min_height,
        )
        selected_assets.append(selected)
        next_request["selected_candidate_id"] = candidate.get("candidate_id")
        if selected.get("status") == "available":
            next_request["status"] = "selected"
            identity = _candidate_identity(candidate)
            if identity:
                used_sources.add(identity)
        else:
            next_request["status"] = selected.get("status", "download_failed")
            next_request["download_error"] = selected.get("reason", "")
        next_requests.append(next_request)
    downloaded["requests"] = next_requests
    downloaded["selected_assets"] = selected_assets
    if any(asset.get("status") == "available" for asset in selected_assets):
        downloaded["status"] = "downloaded"
    return downloaded


def _concept_svg(query: str, accent: str) -> str:
    safe_title = escape(_clean_query(query), quote=True)
    if "data" in query.lower() or "数据" in query:
        motif = """
  <g opacity="0.82">
    <rect x="130" y="160" width="220" height="150" rx="3"/>
    <rect x="390" y="160" width="220" height="150" rx="3"/>
    <rect x="650" y="160" width="220" height="150" rx="3"/>
    <rect x="910" y="160" width="160" height="150" rx="3"/>
    <path d="M180 520H1010M180 610H910M180 700H980"/>
    <circle cx="180" cy="520" r="18"/><circle cx="1010" cy="520" r="18"/>
    <circle cx="180" cy="610" r="18"/><circle cx="910" cy="610" r="18"/>
    <circle cx="180" cy="700" r="18"/><circle cx="980" cy="700" r="18"/>
  </g>"""
    elif "vision" in query.lower() or "视觉" in query:
        motif = """
  <g opacity="0.86">
    <path d="M150 450C300 250 500 180 620 180C760 180 940 270 1050 450C910 640 750 710 620 710C470 710 300 630 150 450Z"/>
    <circle cx="620" cy="450" r="155"/>
    <circle cx="620" cy="450" r="58" fill="none"/>
    <path d="M330 820C465 760 770 760 910 820"/>
    <path d="M470 115L520 245M755 115L710 245"/>
  </g>"""
    else:
        motif = """
  <g opacity="0.82">
    <circle cx="300" cy="300" r="88"/>
    <circle cx="610" cy="460" r="122"/>
    <circle cx="910" cy="260" r="76"/>
    <path d="M375 340L505 410M730 405L845 305"/>
    <path d="M210 760C390 610 760 610 990 760"/>
    <path d="M240 835H960"/>
  </g>"""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 900" role="img" aria-label="{safe_title}">
  <rect width="1200" height="900" fill="#f4f0e8"/>
  <rect x="52" y="52" width="1096" height="796" fill="none" stroke="#10233f" stroke-width="2" opacity="0.22"/>
  <g fill="none" stroke="#10233f" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">{motif}
  </g>
  <circle cx="1030" cy="720" r="86" fill="{accent}" opacity="0.18"/>
  <path d="M100 110H420M100 790H420M780 110H1100M780 790H1100" stroke="{accent}" stroke-width="10" opacity="0.55"/>
</svg>
"""


def _write_generated_concept_asset(request: dict, images_dir: Path, index: int) -> dict:
    images_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_asset_slug(request.get('asset_id') or f'generated-{index}')}.svg"
    target = images_dir / filename
    accent = ["#315f8c", "#b04a3a", "#70815b", "#c29a37"][index % 4]
    target.write_text(_concept_svg(request.get("query", ""), accent), encoding="utf-8")
    return {
        "asset_id": request.get("asset_id", filename),
        "provider": "chora-generated",
        "source_type": "generated_svg",
        "status": "available",
        "filename": filename,
        "render_path": f"assets/images/{filename}",
        "target_pages": request.get("target_pages", []),
        "target_insight_index": request.get("target_insight_index"),
        "role": request.get("role", ""),
        "caption": request.get("query", "Concept visual"),
        "object_position": "center 50%",
        "license_status": "generated-by-chora",
        "preferred_recipe": request.get("preferred_recipe", ""),
    }


def _ai_fallback(
    materialized: dict,
    images_dir: Path,
    *,
    category: str | None = None,
    theme: str | None = None,
    max_ai: int = AI_MAX_PER_PACKAGE,
) -> dict:
    """戊项 C 通道兜底：未被任何 available 候选满足的 evidence/cover_hero request → 调 Gemini AI 生图。

    复用 Chora 已有的 `generate_cover.py`（Gemini 3 Pro Image）。按上游
    `references/production-workflow.md` "Generated Images" 章节：克制地用，
    每图卡组最多 AI_MAX_PER_PACKAGE (2) 张。

    命中本地缓存（同 role/query/target_pages/theme 哈希）→ 不调 API，直接返回。
    """
    from distribution_pipeline.assets.ai_image.gateway import generate_ai_asset

    if is_ai_disabled():
        return materialized

    selected_assets = list(materialized.get("selected_assets", []))
    available_pages = {
        page
        for asset in selected_assets
        if asset.get("status") == "available"
        for page in asset.get("target_pages", [])
    }
    next_requests = []
    ai_count = sum(1 for a in selected_assets if a.get("provider") == "chora-ai-generated")
    for index, request in enumerate(materialized.get("requests", []), start=1):
        next_request = dict(request)
        target_pages = next_request.get("target_pages", [])
        has_visual = any(page in available_pages for page in target_pages)
        if not has_visual and should_generate_via_ai(request, selected_assets):
            if ai_count >= max_ai:
                next_request["status"] = "skipped_ai_quota"
                next_requests.append(next_request)
                continue
            # 1) 缓存命中
            cached = lookup_cache(
                images_dir,
                role=request.get("role", "evidence"),
                query=request.get("query", ""),
                target_pages=target_pages,
                theme=theme,
            )
            if cached is not None:
                selected_assets.append(cached)
                available_pages.update(target_pages)
                next_request["status"] = "ai_cache_hit"
                ai_count += 1
                next_requests.append(next_request)
                continue
            # 2) 调 Gemini
            try:
                generated = generate_ai_asset(
                    request=request,
                    images_dir=images_dir,
                    category=category,
                    theme=theme,
                    prefer_png=True,
                )
            except Exception as exc:
                # 上游 "Log & Continue" 原则：AI 失败不阻塞
                next_request["status"] = f"ai_failed:{type(exc).__name__}"
                next_requests.append(next_request)
                continue
            if generated.get("status") == "available":
                selected_assets.append(generated)
                available_pages.update(target_pages)
                next_request["status"] = "ai_generated"
                ai_count += 1
                remember_in_cache(
                    images_dir,
                    role=request.get("role", "evidence"),
                    query=request.get("query", ""),
                    target_pages=target_pages,
                    theme=theme,
                    asset=generated,
                )
            else:
                next_request["status"] = generated.get("status", "ai_failed")
        next_requests.append(next_request)
    materialized["requests"] = next_requests
    materialized["selected_assets"] = selected_assets
    if any(asset.get("status") == "available" for asset in selected_assets):
        materialized["status"] = "materialized"
    return materialized


def _sources_markdown(plan: dict) -> str:
    lines = [
        "# 图片来源与搜索计划",
        "",
        "本文件由 Chora 自动生成，用于记录本地素材、外部搜索入口与版权判断状态。",
        "",
        "## 已复制本地素材",
    ]
    local_assets = plan.get("local_assets", [])
    if local_assets:
        for asset in local_assets:
            lines.append(
                f"- `{asset.get('filename', asset.get('asset_id'))}` ← `{asset.get('source_path', '')}`；"
                f"用途：{', '.join(asset.get('target_pages', [])) or '未分配'}；版权状态：{asset.get('license_status', 'unknown')}"
            )
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 外部搜索计划"])
    for request in plan.get("requests", []):
        lines.append("")
        lines.append(f"### {request.get('asset_id')} · {request.get('role')}")
        lines.append(f"- 目标页面：{', '.join(request.get('target_pages', []))}")
        if request.get("target_insight_index") is not None:
            lines.append(f"- 目标洞察：{request.get('target_insight_index')}")
        lines.append(f"- 搜索词：`{request.get('query', '')}`")
        lines.append(f"- 建议版式：`{request.get('preferred_recipe', '')}`")
        lines.append(f"- 版权状态：{request.get('license_status', 'unverified')}")
        if request.get("candidate_error"):
            lines.append(f"- 候选抓取错误：{request.get('candidate_error')}")
        for error in request.get("candidate_errors", []):
            lines.append(f"- 候选抓取错误：{error.get('provider', 'unknown')} · {error.get('error', '')}")
        if request.get("download_error"):
            lines.append(f"- 下载错误：{request.get('download_error')}")
        for candidate in request.get("candidates", []):
            lines.append(
                f"- 候选：{candidate.get('provider', 'unknown')} · "
                f"{candidate.get('author', 'unknown')} · {candidate.get('source_url', '')}"
            )
        for provider, url in request.get("search_urls", {}).items():
            lines.append(f"- {provider}: {url}")

    selected_assets = plan.get("selected_assets", [])
    lines.extend(["", "## 已下载外部素材"])
    if selected_assets:
        for asset in selected_assets:
            lines.append(
                f"- `{asset.get('filename', asset.get('asset_id'))}` ← {asset.get('source_url', '')}；"
                f"图源：{asset.get('provider', 'unknown')}；作者：{asset.get('author', 'unknown')}；"
                f"用途：{', '.join(asset.get('target_pages', [])) or '未分配'}；"
                f"目标洞察：{asset.get('target_insight_index', '未绑定')}；"
                f"版权状态：{asset.get('license_status', 'unverified')}；"
                f"状态：{asset.get('status', 'unknown')}"
            )
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 图源说明"])
    for provider, note in plan.get("providers", {}).items():
        lines.append(f"- {provider}: {note}")
    lines.append("")
    return "\n".join(lines)


def materialize_image_assets(
    plan: dict | None,
    assets_dir: Path,
    *,
    image_asset_mode: str = "plan",
    category: str | dict | None = None,
    theme: str | None = None,
    fetch_json=None,
    fetch_bytes=None,
) -> dict:
    if not plan:
        return {
            "version": 1,
            "status": "empty",
            "local_assets": [],
            "requests": [],
            "providers": PROVIDER_NOTES,
        }
    assets_dir = Path(assets_dir)
    images_dir = assets_dir / "images"
    if image_asset_mode not in ("plan", "candidates", "download"):
        raise ValueError(f"Unknown image asset mode: {image_asset_mode}")

    materialized = copy.deepcopy(plan)
    if image_asset_mode in ("candidates", "download"):
        materialized = enrich_image_candidates(
            materialized,
            fetch_json=fetch_json or default_fetch_json,
        )
    if image_asset_mode == "download":
        materialized = download_selected_assets(
            materialized,
            assets_dir,
            fetch_bytes=fetch_bytes,
        )
    materialized["local_assets"] = [
        _copy_local_asset(asset, images_dir) for asset in plan.get("local_assets", [])
    ]
    materialized.setdefault("selected_assets", [])
    # 戊项 C 通道：未满足的 evidence/cover_hero → 调 Gemini AI 生图兜底
    # plan 模式（默认）只写搜索计划，按 upstream "Daily 后处理必须记录并继续"
    # 规则不得生成本地 fallback；candidates/download 模式才允许调 AI。
    if image_asset_mode in ("candidates", "download"):
        category_key = category.get("key") if isinstance(category, dict) else category
        materialized = _ai_fallback(materialized, images_dir, category=category_key, theme=theme)
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / "image_assets.json").write_text(
        json.dumps(materialized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (assets_dir / "SOURCES.md").write_text(_sources_markdown(materialized), encoding="utf-8")
    return materialized
