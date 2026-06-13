import re
import shutil
from html import escape
from pathlib import Path

from distribution_pipeline.assets.image_assets import materialize_image_assets
from distribution_pipeline.renderers.guizang.page_planner import build_xhs_pages
from distribution_pipeline.renderers.guizang.page_planner import content_profile
from distribution_pipeline.renderers.guizang.recipes import render_page_section
from distribution_pipeline.renderers.guizang.render_script import build_render_script, build_xhs_render_targets
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
    return re.sub(r"<title>.*?</title>", f"<title>{safe_title} · Chora Distribution</title>", html, count=1, flags=re.S)


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
        shutil.copyfile(vendor_path("magazine-bg-webgl.js"), assets_dir / "magazine-bg-webgl.js")


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
    joined = "，".join(
        _strip_punctuation(line)
        for line in cover_lines
        if str(line or "").strip()
    )
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


def _wechat_section_shell(section_id: str, poster_class: str, inner: str) -> str:
    return f"""
    <section class="poster {poster_class}" id="{_e(section_id)}">
      <canvas class="mag-bg" data-bg="ink-flow"></canvas>
      <div class="paper-wash"></div>
      <div class="grain"></div>
      {inner}
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
        image_html = f"""
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


def _render_wechat_pair_preview(copy: dict, source: dict, image: dict) -> str:
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
        {"selector": "#wechat-21x9", "filename": "wechat-21x9-cover.png"},
        {"selector": "#wechat-1x1", "filename": "wechat-1x1-cover.png"},
        {"selector": "#wechat-cover-pair-preview", "filename": "wechat-cover-pair-preview.png"},
    ]


def render_guizang_xhs_package(
    package: dict,
    package_dir: Path,
    max_cards: int | None = None,
    mode: str = "editorial",
    theme: str = "indigo-porcelain",
    image_asset_mode: str = "plan",
) -> list[Path]:
    package_dir = Path(package_dir)
    xhs_dir = package_dir / "xhs"
    xhs_dir.mkdir(parents=True, exist_ok=True)

    resolved_theme = _auto_theme(package, mode, theme)
    theme_spec = resolve_theme(mode, resolved_theme)
    _copy_assets(xhs_dir, mode)
    brand = _copy_brand_assets(xhs_dir, package.get("brand"))
    image_assets = materialize_image_assets(
        package.get("image_assets"),
        xhs_dir / "assets",
        image_asset_mode=image_asset_mode,
    )
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
    post_path.write_text(build_xhs_publish_md(package["source"], package["insights"], brand=brand), encoding="utf-8")
    render_path.write_text(build_render_script("index.html", build_xhs_render_targets(pages)), encoding="utf-8")
    return [html_path, post_path, render_path]


def render_guizang_wechat_package(
    package: dict,
    package_dir: Path,
    mode: str = "editorial",
    theme: str = "indigo-porcelain",
    image_asset_mode: str = "plan",
) -> list[Path]:
    if mode != "editorial":
        raise NotImplementedError("Guizang wechat renderer currently supports editorial mode")

    package_dir = Path(package_dir)
    wechat_dir = package_dir / "wechat"
    wechat_dir.mkdir(parents=True, exist_ok=True)

    resolved_theme = _auto_theme(package, mode, theme)
    theme_spec = resolve_theme(mode, resolved_theme)
    _copy_assets(wechat_dir, mode)
    image_assets = materialize_image_assets(
        package.get("image_assets"),
        wechat_dir / "assets",
        image_asset_mode=image_asset_mode,
    )
    package = {**package, "image_assets": image_assets}
    cover_copy = _wechat_cover_copy(package)
    source = package["source"]
    cover_image = _asset_by_id(image_assets, "source-cover")
    sections = [
        _render_wechat_wide(cover_copy, source, cover_image),
        _render_wechat_square(cover_copy, source),
        _render_wechat_pair_preview(cover_copy, source, cover_image),
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
