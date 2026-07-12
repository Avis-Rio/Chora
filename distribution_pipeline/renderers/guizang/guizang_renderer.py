import re
import shutil
from html import escape
from pathlib import Path

from distribution_pipeline.assets.image_assets import materialize_image_assets
from distribution_pipeline.renderers.guizang.category_router import detect_rednote_category
from distribution_pipeline.renderers.guizang.page_planner import build_xhs_pages, content_profile
from distribution_pipeline.renderers.guizang.recipes import render_page_section
from distribution_pipeline.renderers.guizang.render_script import (
    build_render_script,
    build_xhs_render_targets,
)
from distribution_pipeline.renderers.guizang.template_loader import load_template, vendor_path
from distribution_pipeline.renderers.guizang.theme import resolve_theme
from distribution_pipeline.renderers.xhs_copy import DEFAULT_CHORA_URL, build_xhs_publish_md

POSTERS_MARKER = "<!-- POSTERS_HERE -->"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RHIZOMATA_QR = PROJECT_ROOT / "frontend" / "assets" / "rhizomata-qr.png"


def _e(value) -> str:
    return escape(str(value or ""), quote=True)


def _replace_html_attribute(html: str, attribute: str, value: str) -> str:
    html_tag_match = re.search(r"<html\b[^>]*>", html)
    if not html_tag_match:
        raise ValueError("Guizang template is missing <html> tag")
    html_tag = html_tag_match.group(0)
    if re.search(rf'\b{attribute}="[^"]*"', html_tag):
        next_tag = re.sub(rf'\b{attribute}="[^"]*"', f'{attribute}="{value}"', html_tag)
    else:
        next_tag = html_tag[:-1] + f' {attribute}="{value}">'
    return html[: html_tag_match.start()] + next_tag + html[html_tag_match.end() :]


def _set_title(html: str, title: str) -> str:
    safe_title = escape(str(title or "Chora"), quote=False)
    return re.sub(
        r"<title>.*?</title>", f"<title>{safe_title} · Chora Distribution</title>", html, count=1, flags=re.S
    )


def _inject_posters(template: str, sections: list[str]) -> str:
    if POSTERS_MARKER not in template:
        raise ValueError("Guizang template is missing POSTERS_HERE marker")
    before, after = template.rsplit(POSTERS_MARKER, 1)
    main_end = after.find("</main>")
    if main_end == -1:
        raise ValueError("Guizang template is missing </main>")
    return before + POSTERS_MARKER + "\n" + "\n\n".join(sections) + "\n\n" + after[main_end:]


def _copy_assets(target_dir: Path, mode: str) -> None:
    assets_dir = target_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    if mode == "editorial":
        shutil.copyfile(vendor_path("assets/magazine-bg-webgl.js"), assets_dir / "magazine-bg-webgl.js")


def _copy_brand_assets(target_dir: Path, brand: dict | None = None) -> dict:
    resolved = {
        "chora_url": DEFAULT_CHORA_URL,
        "rhizomata_name": "Rhizomata",
        **(brand or {}),
    }
    qr_source = Path(resolved.get("rhizomata_qr_source") or DEFAULT_RHIZOMATA_QR)
    if qr_source.exists():
        brand_dir = target_dir / "assets" / "brand"
        brand_dir.mkdir(parents=True, exist_ok=True)
        qr_target = brand_dir / "rhizomata-qr.png"
        shutil.copyfile(qr_source, qr_target)
        resolved["rhizomata_qr"] = "assets/brand/rhizomata-qr.png"
    return resolved


def _auto_theme(package: dict, mode: str, theme: str) -> str:
    if theme != "auto":
        return theme
    if mode == "swiss":
        return "ikb"
    profile = content_profile(package.get("source", {}), package.get("insights", []))
    if profile == "creator-growth":
        return "kraft-paper"
    if profile == "solitude-psychology":
        return "midnight-ink"
    if profile == "ai-tech":
        return "indigo-porcelain"
    return "ink-classic"


def _select_mode_heuristic(package: dict, target: str) -> str:
    """回退啟發式：基於 content_profile / category / 關鍵詞計數。"""
    source = package.get("source", {})
    insights = package.get("insights", [])
    profile = content_profile(source, insights)
    category = detect_rednote_category(source, insights)
    text = " ".join(
        [
            str(source.get("title", "")),
            str(source.get("channel", "")),
            " ".join(str(tag) for tag in source.get("tags", [])),
            " ".join(str(item.get("title", "")) for item in insights[:6]),
            " ".join(str(item.get("body", "")) for item in insights[:3]),
        ]
    ).lower()

    if category.get("key") in {"workplace", "recommend", "fitness", "makeup"}:
        return "swiss"
    if profile == "creator-growth":
        return "swiss"
    if profile == "ai-tech" and any(
        word in text for word in ("token", "成本", "价格", "指标", "数据", "算力", "增长", "%", "倍")
    ):
        return "swiss"
    return "editorial"


def _select_mode_via_llm(package: dict, target: str) -> str | None:
    """調外部 LLM 根據內容自定 mode（editorial/swiss）。

    設計：環境變量 `CHORA_DISTRIBUTION_MODE_LLM_URL` 提供 OpenAI-compatible 端點時啟用；
    否則返回 None（讓 fallback 接管）。當前 sandbox 網絡受限，內部默認走啟發式。
    """
    import os

    url = os.environ.get("CHORA_DISTRIBUTION_MODE_LLM_URL", "").strip()
    api_key = os.environ.get("CHORA_DISTRIBUTION_MODE_LLM_KEY", "").strip()
    model = os.environ.get("CHORA_DISTRIBUTION_MODE_LLM_MODEL", "claude-sonnet-4-20250514")
    if not url or not api_key:
        return None

    source = package.get("source", {})
    insights = package.get("insights", [])
    payload_text = (
        f"標題：{source.get('title','')}\n"
        f"標籤：{', '.join(source.get('tags', []))}\n"
        f"洞察（前 3 條）：\n"
        + "\n".join(f"- {i.get('title','')}：{i.get('body','')[:80]}" for i in insights[:3])
    )
    prompt = (
        "你是視覺風格策劃。基於以下內容，選擇最契合的卡片風格（僅返回模式名）：\n"
        "- editorial：文學 / 敘事 / 哲思 / 人物 / 社會議題\n"
        "- swiss：科技 / 數據 / 結構 / 商業 / 投資 / 效率\n\n"
        f"{payload_text}\n\n模式："
    )

    try:
        import requests  # type: ignore[import-not-found]

        response = requests.post(
            url,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 16,
                "temperature": 0.1,
            },
            timeout=15,
        )
    except Exception as exc:  # noqa: BLE001 - any network failure → fallback
        print(f"[guizang_mode_llm] LLM 調用失敗: {exc}")
        return None
    if response.status_code != 200:
        print(f"[guizang_mode_llm] 非 200: {response.status_code}")
        return None
    try:
        result = response.json()
        text = (result.get("choices", [{}])[0].get("message", {}).get("content") or "").strip().lower()
    except Exception:
        return None
    if "swiss" in text:
        return "swiss"
    if "editorial" in text:
        return "editorial"
    return None


def resolve_guizang_mode(package: dict, requested: str = "editorial", target: str = "xhs") -> str:
    """解析當前渲染應使用的 Guizang mode（editorial/swiss）。

    requested:
      - "editorial" / "swiss" → 強制指定
      - "auto" → 走啟發式
      - "llm" → 優先 LLM 自定，失敗回退啟發式
    """
    if requested not in ("auto", "llm"):
        return requested
    if requested == "llm":
        llm_mode = _select_mode_via_llm(package, target)
        if llm_mode in ("editorial", "swiss"):
            return llm_mode
    return _select_mode_heuristic(package, target)


def _asset_by_id(image_assets: dict, asset_id: str) -> dict:
    for group in ("local_assets", "selected_assets"):
        for asset in image_assets.get(group, []):
            if asset.get("asset_id") == asset_id and asset.get("render_path"):
                return asset
    return {}


def _strip_punctuation(text: str) -> str:
    return str(text or "").strip().strip("。.!！?？；;：:")


def _break_title(text: str, first_limit: int = 14, second_limit: int = 16) -> list[str]:
    clean = _strip_punctuation(text)
    if not clean:
        return ["Chora"]
    for mark in ("，", "、", "：", "；", ",", ":", "|", "｜", "—", "-"):
        pos = clean.find(mark)
        if 4 <= pos <= first_limit:
            left = clean[:pos].strip()
            right = clean[pos + 1 :].strip()
            return [left, right[:second_limit]] if right else [left]
    if len(clean) <= first_limit:
        return [clean]
    return [clean[:first_limit], clean[first_limit : first_limit + second_limit]]


def _short_wechat_title(source: dict, cover_lines: list[str]) -> list[str]:
    text = f"{source.get('title', '')} {' '.join(cover_lines)}"
    lowered = text.lower()
    if "grow an audience" in lowered or "followers" in lowered or "粉丝" in text:
        return ["零粉丝", "增长"]
    if "people disappear" in lowered or "being alone" in lowered or "孤独" in text:
        return ["选择", "消失"]
    if "gemini" in lowered or "谷歌ai" in lowered or "谷歌 AI" in text:
        return ["谷歌 AI", "翻身战"]
    if "token" in lowered or "成本" in text:
        return ["AI 成本"]
    for line in cover_lines:
        clean = _strip_punctuation(line)
        if 2 <= len(clean) <= 10:
            return _break_title(clean, first_limit=6, second_limit=6)
    clean = _strip_punctuation(str(source.get("title", "")))
    return _break_title(clean, first_limit=6, second_limit=6)


def _wide_wechat_title(source: dict, cover_lines: list[str]) -> str:
    text = f"{source.get('title', '')} {' '.join(cover_lines)}"
    lowered = text.lower()
    if "grow an audience" in lowered or "followers" in lowered or "粉丝" in text:
        return "零粉丝增长，不靠算法"
    if "people disappear" in lowered or "being alone" in lowered or "孤独" in text:
        return "为什么人们选择消失"
    if "gemini" in lowered or "谷歌ai" in lowered or "谷歌 AI" in text:
        return "谷歌 AI 慢半拍，但还没输"
    if "token" in lowered or "成本" in text:
        return "AI 成本重新分配权力"
    joined = "，".join(_strip_punctuation(line) for line in cover_lines if str(line or "").strip())
    if 4 <= len(joined) <= 18:
        return joined
    clean = _strip_punctuation(str(source.get("title", "")))
    return clean[:18] if clean else "Chora"


def _wechat_cover_copy(package: dict) -> dict:
    pages = build_xhs_pages(package, max_cards=3, mode="editorial")
    cover = pages[0] if pages else {}
    cover_lines = cover.get("title_lines") or _break_title(package["source"].get("title", "Chora"))
    return {
        "long_title": cover.get("title") or "\n".join(cover_lines),
        "long_lines": cover_lines,
        "wide_title": _wide_wechat_title(package["source"], cover_lines),
        "short_lines": _short_wechat_title(package["source"], cover_lines),
        "body": cover.get("body") or f"{package['source'].get('channel', 'Unknown')} · Chora 深度内容",
    }


def _wechat_section_shell(section_id: str, poster_class: str, inner: str, decorative: bool = True) -> str:
    layers = (
        """
      <canvas class="mag-bg" data-bg="ink-flow" style="display:block"></canvas>
      <div class="paper-wash" style="display:block"></div>
      <div class="grain" style="display:block"></div>
"""
        if decorative
        else ""
    )
    return f"""
    <section class="poster {poster_class}" id="{_e(section_id)}">
{layers}      {inner}
    </section>"""


def _render_wechat_wide(copy: dict, source: dict, image: dict, section_id: str = "wechat-21x9") -> str:
    title = _e(copy.get("wide_title") or " ".join(copy["long_lines"]))
    image_html = ""
    if image.get("render_path"):
        image_html = f"""
          <figure class="frame-img r-16x9" style="min-height:460px">
            <img src="{_e(image.get("render_path"))}" alt="{_e(image.get("caption") or "source cover")}" style="object-position:{_e(image.get("object_position", "center 50%"))}">
            <figcaption class="img-cap">SOURCE · {_e(source.get("channel", "Chora"))}</figcaption>
          </figure>"""
    else:
        image_html = """
          <div style="min-height:460px;border:1px solid var(--line);background:rgba(var(--accent-rgb),.06);display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:44px;color:rgba(var(--accent-rgb),.42);letter-spacing:.18em;text-transform:uppercase">
            CHORA
          </div>"""
    inner = f"""
      <div class="content" style="display:grid;grid-template-columns:minmax(0,1fr) 560px;gap:56px;align-items:center">
        <div class="stack gap-4">
          <div class="issue-row">
            <span>WeChat · 21:9</span><span class="dot"></span><span>{_e(source.get("channel", "Chora"))}</span>
          </div>
          <h1 class="h-display" style="font-size:96px;line-height:1.08">{title}</h1>
          <p class="lead" style="font-size:34px;line-height:1.42;max-width:980px">{_e(copy["body"])}</p>
          <hr class="rule-accent" style="width:220px;height:4px">
        </div>
{image_html}
      </div>"""
    return _wechat_section_shell(section_id, "wide", inner)


def _render_wechat_square(copy: dict, source: dict, section_id: str = "wechat-1x1") -> str:
    title = "<br>".join(_e(line) for line in copy["short_lines"] if str(line or "").strip())
    inner = f"""
      <div class="content stack gap-4" style="justify-content:center;align-items:center;text-align:center">
        <p class="kicker">WeChat · 1:1 · {_e(source.get("channel", "Chora"))}</p>
        <h1 class="h-display" style="font-size:118px;line-height:1.08">{title}</h1>
        <hr class="rule-accent" style="width:180px;height:4px">
        <p class="h-sub">Chora Archive</p>
      </div>"""
    return _wechat_section_shell(section_id, "square", inner)


def _render_wechat_swiss_wide(copy: dict, source: dict, image: dict, section_id: str = "wechat-21x9") -> str:
    title = _e(copy.get("wide_title") or " ".join(copy["long_lines"]))
    stats = [
        {"num": "01", "lbl": "INSIGHT"},
        {"num": source.get("channel", "Chora")[:8], "lbl": "SOURCE"},
    ]
    stats_html = "\n".join(f"""
          <div class="stat-block" style="padding:20px 28px;background:rgba(var(--ink-rgb),.05);border-left:3px solid var(--accent)">
            <p class="num" style="font-size:48px;line-height:1">{_e(s['num'])}</p>
            <p class="lbl" style="font-size:16px;letter-spacing:.12em">{_e(s['lbl'])}</p>
          </div>""" for s in stats)
    image_html = ""
    if image.get("render_path"):
        image_html = f"""
          <figure class="frame-img r-16x9" style="min-height:360px">
            <img src="{_e(image.get("render_path"))}" alt="{_e(image.get("caption") or "source cover")}" style="object-position:{_e(image.get("object_position", "center 50%"))}">
          </figure>"""
    else:
        image_html = """
          <div style="min-height:360px;border:1px solid var(--line);background:rgba(var(--accent-rgb),.06);display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:44px;color:rgba(var(--accent-rgb),.42);letter-spacing:.18em;text-transform:uppercase">
            CHORA
          </div>"""
    inner = f"""
      <div class="content" style="display:grid;grid-template-columns:minmax(0,1fr) 520px;gap:40px;align-items:center;padding:var(--sp-10) var(--sp-12)">
        <div class="stack gap-4">
          <div class="issue-row">
            <span>WeChat · 21:9</span><span class="dot"></span><span>{_e(source.get("channel", "Chora"))}</span>
          </div>
          <h1 class="h-display" style="font-size:72px;line-height:1.06">{title}</h1>
          <p class="lead" style="font-size:26px;line-height:1.38;max-width:900px">{_e(copy["body"])}</p>
          <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:8px">
{stats_html}
          </div>
        </div>
{image_html}
      </div>"""
    return _wechat_section_shell(section_id, "wide swiss", inner, decorative=False)


def _render_wechat_swiss_square(copy: dict, source: dict, section_id: str = "wechat-1x1") -> str:
    title = "<br>".join(_e(line) for line in copy["short_lines"] if str(line or "").strip())
    inner = f"""
      <div class="content stack gap-4" style="justify-content:center;align-items:center;text-align:center">
        <p class="kicker" style="font-size:18px">WeChat · 1:1 · {_e(source.get("channel", "Chora"))}</p>
        <h1 class="h-display" style="font-size:88px;line-height:1.06">{title}</h1>
        <hr class="rule-accent" style="width:180px;height:4px">
        <div style="display:flex;gap:48px;justify-content:center;margin-top:12px">
          <div style="text-align:center">
            <p style="font-family:var(--mono);font-size:44px;line-height:1;color:var(--accent)">01</p>
            <p class="t-meta" style="font-size:18px">ISSUE</p>
          </div>
          <div style="text-align:center">
            <p style="font-family:var(--mono);font-size:44px;line-height:1;color:var(--accent)">SWISS</p>
            <p class="t-meta" style="font-size:18px">STYLE</p>
          </div>
        </div>
      </div>"""
    return _wechat_section_shell(section_id, "square swiss", inner, decorative=False)


def _render_wechat_pair_preview(copy: dict, source: dict, image: dict, mode: str = "editorial") -> str:
    if mode == "swiss":
        wide = _render_wechat_swiss_wide(copy, source, image, section_id="wechat-preview-wide")
        square = _render_wechat_swiss_square(copy, source, section_id="wechat-preview-square")
    else:
        wide = _render_wechat_wide(copy, source, image, section_id="wechat-preview-wide")
        square = _render_wechat_square(copy, source, section_id="wechat-preview-square")
    return f"""
    <section class="pair-preview" id="wechat-cover-pair-preview" style="width:2400px;min-height:820px;grid-template-columns:1260px 648px;grid-template-rows:700px;gap:48px;overflow:hidden">
      <div class="preview-wide">
        <div class="preview-label">21:9 Main Cover</div>
        <div style="width:1260px;height:540px;overflow:hidden">
          <div style="transform:scale(.6);transform-origin:top left;width:2100px;height:900px">
{wide}
          </div>
        </div>
      </div>
      <div class="preview-square">
        <div class="preview-label">1:1 Square Cover</div>
        <div style="width:648px;height:648px;overflow:hidden">
          <div style="transform:scale(.6);transform-origin:top left;width:1080px;height:1080px">
{square}
          </div>
        </div>
      </div>
    </section>"""


def build_wechat_render_targets() -> list[dict]:
    return [
        {"selector": "#wechat-21x9", "filename": "wechat-21x9-cover.png", "width": 2100, "height": 900},
        {"selector": "#wechat-1x1", "filename": "wechat-1x1-cover.png", "width": 1080, "height": 1080},
        {
            "selector": "#wechat-cover-pair-preview",
            "filename": "wechat-cover-pair-preview.png",
            "width": 2400,
            "height": 844,
        },
    ]


def render_guizang_xhs_package(
    package: dict,
    package_dir: Path,
    max_cards: int | None = None,
    mode: str = "editorial",
    theme: str = "indigo-porcelain",
    image_asset_mode: str = "plan",
) -> list[Path]:
    mode = resolve_guizang_mode(package, mode, target="xhs")
    package_dir = Path(package_dir)
    xhs_dir = package_dir / "xhs"
    xhs_dir.mkdir(parents=True, exist_ok=True)

    resolved_theme = _auto_theme(package, mode, theme)
    theme_spec = resolve_theme(mode, resolved_theme)
    category = detect_rednote_category(package.get("source", {}), package.get("insights", []))
    _copy_assets(xhs_dir, mode)
    brand = _copy_brand_assets(xhs_dir, package.get("brand"))
    image_assets = materialize_image_assets(
        package.get("image_assets"),
        xhs_dir / "assets",
        image_asset_mode=image_asset_mode,
        category=category,
        theme=resolved_theme,
    )
    image_assets["_render_root"] = str(xhs_dir)
    package = {**package, "image_assets": image_assets, "brand": brand}
    pages = build_xhs_pages(package, max_cards=max_cards, mode=mode)
    sections = [render_page_section(page, mode=mode) for page in pages]
    html = load_template(mode)
    html = _replace_html_attribute(html, theme_spec["attribute"], theme_spec["value"])
    html = _set_title(html, package["source"].get("title", "Chora"))
    html = _inject_posters(html, sections)

    html_path = xhs_dir / "index.html"
    post_path = xhs_dir / "post.md"
    render_path = xhs_dir / "render.cjs"
    html_path.write_text(html, encoding="utf-8")
    post_path.write_text(
        build_xhs_publish_md(package["source"], package["insights"], brand=brand), encoding="utf-8"
    )
    render_path.write_text(
        build_render_script("index.html", build_xhs_render_targets(pages)), encoding="utf-8"
    )
    return [html_path, post_path, render_path]


def render_guizang_wechat_package(
    package: dict,
    package_dir: Path,
    mode: str = "editorial",
    theme: str = "indigo-porcelain",
    image_asset_mode: str = "plan",
) -> list[Path]:
    mode = resolve_guizang_mode(package, mode, target="wechat")

    package_dir = Path(package_dir)
    wechat_dir = package_dir / "wechat"
    wechat_dir.mkdir(parents=True, exist_ok=True)

    resolved_theme = _auto_theme(package, mode, theme)
    theme_spec = resolve_theme(mode, resolved_theme)
    category = detect_rednote_category(package.get("source", {}), package.get("insights", []))
    _copy_assets(wechat_dir, mode)
    image_assets = materialize_image_assets(
        package.get("image_assets"),
        wechat_dir / "assets",
        image_asset_mode=image_asset_mode,
        category=category,
        theme=resolved_theme,
    )
    image_assets["_render_root"] = str(wechat_dir)
    package = {**package, "image_assets": image_assets}
    cover_copy = _wechat_cover_copy(package)
    source = package["source"]
    cover_image = _asset_by_id(image_assets, "source-cover")

    if mode == "swiss":
        sections = [
            _render_wechat_swiss_wide(cover_copy, source, cover_image),
            _render_wechat_swiss_square(cover_copy, source),
            _render_wechat_pair_preview(cover_copy, source, cover_image, mode="swiss"),
        ]
    else:
        sections = [
            _render_wechat_wide(cover_copy, source, cover_image),
            _render_wechat_square(cover_copy, source),
            _render_wechat_pair_preview(cover_copy, source, cover_image, mode="editorial"),
        ]

    html = load_template(mode)
    html = _replace_html_attribute(html, theme_spec["attribute"], theme_spec["value"])
    html = _set_title(html, source.get("title", "Chora"))
    html = _inject_posters(html, sections)

    html_path = wechat_dir / "index.html"
    appendix_path = wechat_dir / "appendix.md"
    render_path = wechat_dir / "render.cjs"
    html_path.write_text(html, encoding="utf-8")
    appendix_path.write_text(
        (
            f"主封面：{' / '.join(cover_copy['long_lines'])}\n"
            f"方形封面：{' / '.join(cover_copy['short_lines'])}\n\n"
            f"完整内容见 Chora：{source.get('title', '')}\n\n"
            f"原始来源：{source.get('source_url', '')}\n"
        ),
        encoding="utf-8",
    )
    render_path.write_text(build_render_script("index.html", build_wechat_render_targets()), encoding="utf-8")
    return [html_path, appendix_path, render_path]
