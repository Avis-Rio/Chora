import re
from html import escape

from distribution_pipeline.renderers.guizang.content_allocator import build_copy_slots
from distribution_pipeline.renderers.guizang.screenshot_treatment import render_image_frame as _render_image_frame
from distribution_pipeline.renderers.guizang.title_breaker import semantic_title_lines
from distribution_pipeline.renderers.guizang.title_budget import title_budget_for


SCAFFOLD_LABELS = {"注记", "脉络", "张力", "信号", "判断", "余波", "边界", "后果"}
SCAFFOLD_SEQUENCE = ("注记", "脉络", "张力", "信号", "判断", "余波")


def _e(value) -> str:
    return escape(str(value or ""), quote=True)


def _paragraphs(text: str, limit: int = 5) -> list[str]:
    clean = " ".join(str(text or "").split())
    if not clean:
        return []
    parts = []
    current = ""
    for char in clean:
        current += char
        if char in "。！？；;":
            parts.append(current.strip())
            current = ""
    if current.strip():
        parts.append(current.strip())
    if len(parts) <= 1:
        parts = [clean]
    return parts[:limit]


def _norm_text(text: str) -> str:
    return "".join(
        char
        for char in str(text or "")
        if char.strip() and char not in "，,。.!！?？；;：:、-—“”\"'（）()[]【】"
    )


def _without_repeats(items: list[str], exclude: list[str] | None = None, limit: int = 4) -> list[str]:
    seen = {_norm_text(item) for item in (exclude or []) if _norm_text(item)}
    unique = []
    for item in items:
        clean = str(item or "").strip()
        norm = _norm_text(clean)
        if not clean or not norm:
            continue
        if norm in seen or any(norm in old or old in norm for old in seen):
            continue
        seen.add(norm)
        unique.append(clean)
        if len(unique) >= limit:
            break
    return unique


def _is_scaffold_label(value: str) -> bool:
    return str(value or "").strip() in SCAFFOLD_LABELS


def _split_point_item(point: str) -> tuple[str, str]:
    clean = " ".join(str(point or "").split())
    if not clean:
        return "", ""
    for sep in ("：", ":"):
        pos = clean.find(sep)
        if 1 < pos <= 28:
            title = clean[:pos].strip()
            note = clean[pos + 1 :].strip()
            if title and note:
                return title, note
    parts = _paragraphs(clean, limit=3)
    if len(parts) > 1 and len(_norm_text(parts[0])) <= 28:
        return parts[0], " ".join(parts[1:])
    return "", clean


def _labelled_items(points: list[str], exclude: list[str] | None = None, limit: int = 4) -> list[dict]:
    unique = _without_repeats(points, exclude=exclude, limit=limit)
    items = []
    for idx, point in enumerate(unique, start=1):
        source_title, note = _split_point_item(point)
        items.append(
            {
                "index": f"{idx:02d}",
                "title": SCAFFOLD_SEQUENCE[(idx - 1) % len(SCAFFOLD_SEQUENCE)],
                "source_title": source_title,
                "note": note or point,
            }
        )
    return items


def _item_title(item: dict) -> str:
    source_title = str((item or {}).get("source_title") or "").strip()
    if source_title:
        return source_title
    title = str((item or {}).get("title") or "").strip()
    return "" if _is_scaffold_label(title) else title


def _item_note(item: dict) -> str:
    return str((item or {}).get("note") or "").strip()


def _item_primary(item: dict) -> str:
    return _item_title(item) or _item_note(item)


def _item_secondary(item: dict) -> str:
    title = _item_title(item)
    note = _item_note(item)
    if title and note and _norm_text(title) != _norm_text(note):
        return note
    return ""


def _source_label(text: str, limit: int = 18) -> str:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return ""
    title, note = _split_point_item(clean)
    candidate = title or clean
    if len(candidate) <= limit:
        return candidate
    trimmed = candidate[:limit].rstrip("，,。.!！?？；;：:")
    return f"{trimmed}..."


def _image_caption_label(value: str) -> str:
    clean = " ".join(str(value or "").split()).strip()
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .·/_-]{0,24}", clean):
        return clean
    return _source_label(clean, limit=10)


def _visible_chips(page: dict) -> list[dict]:
    return [chip for chip in (page.get("chips") or []) if not chip.get("generated")]


def _copy_slots(page: dict) -> dict:
    return page.get("copy_slots") or build_copy_slots(page)


def _slot_text(page: dict, key: str, fallback: str = "") -> str:
    value = _copy_slots(page).get(key)
    if isinstance(value, list):
        return " ".join(str(item or "").strip() for item in value if str(item or "").strip())
    return str(value or fallback or "").strip()


def _slot_items(page: dict, key: str = "sentences", limit: int = 4) -> list[dict]:
    values = _copy_slots(page).get(key) or []
    if isinstance(values, str):
        values = [values]
    return _labelled_items([str(value) for value in values if str(value or "").strip()], limit=limit)


def _accent_title(title: str) -> str:
    text = str(title or "")
    if not text:
        return ""

    latin_match = re.match(r"[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+)*", text)
    if latin_match:
        split_at = latin_match.end()
        return f'<span style="color:var(--accent)">{_e(text[:split_at])}</span>{_e(text[split_at:])}'

    for mark in ("，", "：", "、", "；"):
        pos = text.find(mark)
        if 0 < pos <= 14:
            split_at = pos + 1
            return f'<span style="color:var(--accent)">{_e(text[:split_at])}</span>{_e(text[split_at:])}'

    marker_positions = []
    for marker in ("并不是", "不是", "是", "的", "进入", "成为", "正在", "驱使", "反而", "需要", "可能", "可以", "不会", "会"):
        pos = text.find(marker)
        if 2 <= pos <= 10:
            marker_positions.append(pos)
    if marker_positions:
        split_at = min(marker_positions)
        return f'<span style="color:var(--accent)">{_e(text[:split_at])}</span>{_e(text[split_at:])}'

    if len(text) <= 8:
        split_at = len(text)
    else:
        split_at = min(6, len(text))
    return f'<span style="color:var(--accent)">{_e(text[:split_at])}</span>{_e(text[split_at:])}'


def _title_lines_from_value(value, target: int = 11, max_lines: int = 2) -> list[str]:
    if isinstance(value, list):
        lines = [str(line or "").strip() for line in value if str(line or "").strip()]
        if lines:
            max_width = target + 2
            if len(lines) <= max_lines and all(len(line) <= max_width for line in lines):
                return lines
            return semantic_title_lines("".join(lines), target=target, max_lines=max_lines, min_tail=3)
    if isinstance(value, str) and "\n" in value:
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        if lines:
            max_width = target + 2
            if len(lines) <= max_lines and all(len(line) <= max_width for line in lines):
                return lines
            return semantic_title_lines("".join(lines), target=target, max_lines=max_lines, min_tail=3)
    return semantic_title_lines(str(value or ""), target=target, max_lines=max_lines, min_tail=3)


def _budget(page: dict):
    return title_budget_for(page.get("recipe"))


def _section_attrs(page: dict) -> str:
    slots = _copy_slots(page)
    qa_flags = page.get("qa_flags") or []
    if isinstance(qa_flags, str):
        qa_flags = [qa_flags]
    flags = " ".join(str(flag).strip() for flag in qa_flags if str(flag).strip())
    density_ok = slots.get("density_ok")
    if density_ok is None:
        density_ok = page.get("density_ok")
    if density_ok is None:
        density_ok = ""
    elif isinstance(density_ok, bool):
        density_ok = "true" if density_ok else "false"
    return (
        f'data-role="{_e(page.get("role", ""))}" '
        f'data-recipe="{_e(page.get("recipe", ""))}" '
        f'data-title-max-lines="{_e((page.get("title_budget") or {}).get("max_lines", ""))}" '
        f'data-qa-flags="{_e(flags)}" '
        f'data-density-ok="{_e(density_ok)}" '
        f'data-payload-chars="{_e(slots.get("payload_chars", ""))}" '
        f'data-detail-count="{_e(slots.get("detail_count", ""))}"'
    )


def _title_lines(page: dict, target: int | None = None, max_lines: int | None = None) -> list[str]:
    budget = _budget(page)
    target = target or int((page.get("title_budget") or {}).get("line_chars") or budget.line_chars)
    max_lines = max_lines or int((page.get("title_budget") or {}).get("max_lines") or budget.max_lines)
    value = page.get("title_lines") or page.get("display_title") or page.get("title", "")
    return _title_lines_from_value(value, target=target, max_lines=max_lines)


def _title_plain(page: dict, target: int | None = None, max_lines: int | None = None) -> str:
    return "".join(_title_lines(page, target=target, max_lines=max_lines))


def _title_html(page: dict, target: int | None = None, max_lines: int | None = None, accent: bool = False) -> str:
    lines = _title_lines(page, target=target, max_lines=max_lines)
    if accent:
        return "<br>".join(_accent_title(line) for line in lines)
    return "<br>".join(_e(line) for line in lines)


def _title_html_from_text(text: str, target: int = 11, max_lines: int = 2, accent: bool = False) -> str:
    lines = _title_lines_from_value(text, target=target, max_lines=max_lines)
    if accent:
        return "<br>".join(_accent_title(line) for line in lines)
    return "<br>".join(_e(line) for line in lines)


def _title_plain_from_text(text: str, target: int = 11, max_lines: int = 2) -> str:
    return "".join(_title_lines_from_value(text, target=target, max_lines=max_lines))


def _display_number(page: dict) -> str:
    return str(page.get("display_index") or page.get("id", "")[-2:] or "01")


def _takeaway_band(page: dict, exclude: list[str] | None = None) -> str:
    takeaway = str(page.get("reader_takeaway") or "").strip()
    norm = _norm_text(takeaway)
    if not norm:
        return ""
    for item in exclude or []:
        item_norm = _norm_text(item)
        if item_norm and (norm in item_norm or item_norm in norm):
            return ""
    return f"""
        <div class="takeaway-band" style="border-left:4px solid var(--accent);background:rgba(var(--accent-rgb),.08);padding:22px 28px;display:grid;grid-template-columns:190px 1fr;gap:26px;align-items:start">
          <div style="font-family:var(--mono);font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)">why it matters</div>
          <div style="font-family:var(--serif-zh);font-size:30px;line-height:1.38;color:var(--ink)">{_e(takeaway)}</div>
        </div>"""


def _title_style(title: str, base_px: int = 88, page: dict | None = None) -> str:
    """Return inline style fragment using recipe title budget first, length second."""
    budget_px = None
    if page and page.get("title_budget"):
        budget_px = (page.get("title_budget") or {}).get("font_px") or title_budget_for(page.get("recipe")).font_px
    base = int(budget_px or base_px)
    length = len(str(title or ""))
    if length <= 14:
        suffix = ";line-height:1.12" if page and page.get("title_budget") else ""
        return f' style="font-size:{base}px{suffix}"'
    if length <= 20:
        return f' style="font-size:{max(base - 4, 56)}px;line-height:1.14"'
    if length <= 28:
        return f' style="font-size:{max(base - 10, 52)}px;line-height:1.14"'
    if length <= 40:
        return f' style="font-size:{max(base - 24, 42)}px;line-height:1.16"'
    return f' style="font-size:{max(base - 34, 34)}px;line-height:1.18"'


def _footer(page: dict) -> str:
    footer = _e(page.get("footer", "Chora · Rhizomata"))
    cta_footer_style = ' style="border-top:0;padding-top:0"' if page.get("cta") else ""
    return f"""
      <div class="issue-strip"{cta_footer_style}>
        <span>{footer}</span>
        <span>-</span>
        <span>{_e(page.get("id", ""))}</span>
      </div>"""


def _cta_strip(page: dict, variant: str = "editorial") -> str:
    cta = page.get("cta") or {}
    if not cta:
        return ""
    label = cta.get("label", "阅读全文")
    site_label = cta.get("site_label", "Chora")
    url = cta.get("url", "")
    display_url = re.sub(r"^https?://", "", str(url or "")).rstrip("/") or "完整内容见 Chora"
    qr_src = cta.get("qr_src", "")
    qr_label = cta.get("qr_label", "公众号 · Rhizomata")
    qr_name = re.sub(r"^公众号\s*[·・]\s*", "", str(qr_label or "Rhizomata")).strip() or "Rhizomata"
    qr_html = (
        f"""
          <div class="cta-qr" style="width:104px;height:104px;display:flex;align-items:center;justify-content:center;flex:0 0 104px">
            <img src="{_e(qr_src)}" alt="{_e(qr_label)}" style="width:100%;height:100%;object-fit:contain;display:block">
          </div>"""
        if qr_src
        else ""
    )
    if variant == "swiss":
        return f"""
        <div class="cta-strip" style="min-height:122px;display:grid;grid-template-columns:1fr 104px;align-items:center;gap:var(--sp-6)">
          <div style="min-width:0">
            <p class="t-cat" style="margin-bottom:var(--sp-2)">{_e(label)} · {_e(site_label)}</p>
            <p class="lead" style="font-size:20px;line-height:1.24;word-break:break-all;max-width:560px;margin-bottom:var(--sp-2)">{_e(display_url)}</p>
            <p class="t-meta">{_e('关注 ' + qr_name)}</p>
          </div>
{qr_html}
        </div>"""
    return f"""
        <div class="cta-strip" style="margin:14px 0 58px;display:grid;grid-template-columns:1fr 104px;align-items:center;gap:30px">
          <div style="min-width:0">
            <div style="font-family:var(--mono);font-size:15px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)">{_e(label)} · {_e(site_label)}</div>
            <div style="margin-top:8px;font-family:var(--mono);font-size:18px;line-height:1.32;letter-spacing:.02em;color:rgba(var(--ink-rgb),.78);word-break:break-all">{_e(display_url)}</div>
            <div style="margin-top:6px;font-family:var(--serif-zh);font-size:17px;line-height:1.3;color:rgba(var(--ink-rgb),.52)">{_e('关注 ' + qr_name)}</div>
          </div>
{qr_html}
        </div>"""


def _swiss_cta_marker(page: dict) -> str:
    cta = page.get("cta") or {}
    if not cta:
        return ""
    qr_label = cta.get("qr_label", "公众号 · Rhizomata")
    qr_name = re.sub(r"^公众号\s*[·・]\s*", "", str(qr_label or "Rhizomata")).strip() or "Rhizomata"
    qr_src = cta.get("qr_src", "")
    qr_img = (
        f'<img src="{_e(qr_src)}" alt="{_e(qr_label)}" style="width:82px;height:82px;object-fit:contain;display:block">'
        if qr_src
        else ""
    )
    return f"""
          <div class="cta-marker" style="display:grid;grid-template-columns:82px auto;gap:var(--sp-4);align-items:center;justify-content:start;min-width:220px">
            <div class="cta-qr" style="width:82px;height:82px;display:flex;align-items:center;justify-content:center">{qr_img}</div>
            <div style="display:grid;gap:8px">
              <p class="t-meta" style="margin:0;color:rgba(var(--ink-rgb),.48)">WECHAT</p>
              <p class="t-meta" style="margin:0;color:var(--accent);font-size:20px;letter-spacing:.16em">{_e(qr_name.upper())}</p>
            </div>
          </div>"""


def _cta_display_url(cta: dict) -> str:
    url = cta.get("url", "")
    if not url:
        return "完整内容见 Chora"
    display_url = re.sub(r"^https?://", "", str(url)).rstrip("/")
    if display_url and not display_url.lower().startswith("www."):
        display_url = f"www.{display_url}"
    return display_url.upper()


def _swiss_archive_mark(page: dict) -> str:
    display_url = _cta_display_url(page.get("cta") or {})
    return f"""
          <div class="archive-mark" style="display:grid;grid-template-columns:72px minmax(0,1fr);gap:var(--sp-4);align-items:center;min-width:0">
            <svg aria-hidden="true" width="72" height="72" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block;color:var(--ink)">
              <path d="M14 18H58V30H14V18Z" stroke="currentColor" stroke-width="4"/>
              <path d="M18 30H54V56H18V30Z" stroke="currentColor" stroke-width="4"/>
              <path d="M28 39H44" stroke="currentColor" stroke-width="4"/>
              <path d="M52 12V22" stroke="var(--accent)" stroke-width="4"/>
              <path d="M46 18H58" stroke="var(--accent)" stroke-width="4"/>
            </svg>
            <div style="display:grid;gap:10px;min-width:0">
              <p class="t-meta" style="margin:0;color:var(--ink);font-size:20px;letter-spacing:.18em">CHORA ARCHIVE</p>
              <p class="t-meta" style="margin:0;color:rgba(var(--ink-rgb),.48);font-size:14px;letter-spacing:.04em;white-space:nowrap">{_e(display_url)}</p>
            </div>
          </div>"""


def _image_figure(image: dict, fig_label: str = "FIG. 01", ratio: str = "r-4x3") -> str:
    if not image.get("src"):
        return ""
    caption = _image_caption_label(image.get("caption") or image.get("alt") or image.get("asset_id") or "Source image")
    return f"""
        <figure class="frame-img {ratio}">
          <img src="{_e(image.get("src"))}" alt="{_e(caption)}" style="object-position:{_e(image.get("object_position", "center 50%"))}">
          <figcaption class="img-cap">{_e(fig_label)} · {_e(caption)}</figcaption>
        </figure>"""


def _page_items(page: dict, limit: int = 6) -> list[dict]:
    items = page.get("items") or []
    if items:
        normalized = []
        for index, item in enumerate(items[:limit], start=1):
            if isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append({"index": f"{index:02d}", "title": "", "note": str(item or "").strip()})
        return normalized
    points = page.get("points") or _paragraphs(page.get("body", ""), limit=limit)
    labelled = _labelled_items(points, limit=limit)
    if labelled:
        return labelled[:limit]
    return [{"index": "01", "title": page.get("title", ""), "note": page.get("body", "")}]


def _is_sparse_body(page: dict, threshold: int = 140) -> bool:
    return len(_norm_text(page.get("body", ""))) < threshold


def _density_items(page: dict, limit: int = 3, exclude: list[str] | None = None) -> list[dict]:
    chips = _visible_chips(page)
    if chips:
        return chips[:limit]
    slots = _copy_slots(page)
    candidates = []
    for key in ("points", "details", "sentences"):
        values = slots.get(key) or []
        if isinstance(values, str):
            values = [values]
        candidates.extend(str(value or "").strip() for value in values if str(value or "").strip())
    candidates.extend(str(value or "").strip() for value in (page.get("points") or []) if str(value or "").strip())
    candidates.extend(str(value or "").strip() for value in (page.get("details") or []) if str(value or "").strip())
    candidates.extend(_paragraphs(page.get("body", ""), limit=limit + 2))
    items = _labelled_items(candidates, exclude=exclude, limit=limit)
    if items:
        return items
    return []


def _density_panel(
    page: dict,
    label: str = "Reading Field",
    min_height: int = 300,
    exclude: list[str] | None = None,
) -> str:
    number = _display_number(page)
    items = _density_items(page, exclude=exclude)
    cells = "\n".join(
        f"""
            <div style="border-top:1px solid var(--line);padding-top:14px">
              <span style="display:block;font-family:var(--mono);font-size:18px;letter-spacing:.12em;color:var(--accent)">{_e(item.get("index"))}</span>
              <span style="display:block;margin-top:8px;font-family:var(--serif-zh);font-size:20px;line-height:1.4;color:var(--ink);display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical;overflow:hidden">{_e(_item_primary(item))}</span>
            </div>"""
        for item in items
    )
    return f"""
        <div class="density-panel" style="position:relative;margin-top:auto;min-height:{min_height}px;background:rgba(var(--accent-rgb),.055);border:1px solid rgba(var(--accent-rgb),.22);padding:28px 32px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden">
          <div aria-hidden="true" style="position:absolute;left:32px;right:32px;top:84px;bottom:108px;background-image:repeating-linear-gradient(90deg,rgba(var(--accent-rgb),.16) 0 1px,transparent 1px 88px),repeating-linear-gradient(0deg,rgba(var(--accent-rgb),.10) 0 1px,transparent 1px 72px);opacity:.58"></div>
          <div style="position:relative;z-index:1;display:flex;justify-content:space-between;align-items:center;font-family:var(--mono);font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">
            <span>{_e(label)}</span>
            <span>Point {number}</span>
          </div>
          <div style="position:relative;z-index:1;display:grid;grid-template-columns:178px 1fr;gap:34px;align-items:end">
            <div style="font-family:var(--mono);font-size:154px;line-height:.82;letter-spacing:0;color:rgba(var(--accent-rgb),.32)">{_e(number)}</div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:18px">
{cells}
            </div>
          </div>
        </div>"""


def _editorial_shell(page: dict, inner: str) -> str:
    return f"""
    <section class="poster xhs" id="{_e(page.get("id"))}" {_section_attrs(page)}>
      <canvas class="mag-bg" data-bg="ink-flow"></canvas>
      <div class="paper-wash"></div>
      <div class="grain"></div>
      {inner}
      {_footer(page)}
    </section>"""


def _render_editorial_cover(page: dict) -> str:
    title_lines = page.get("title_lines") or [page.get("title")]
    title = "<br>".join(_e(line) for line in title_lines if str(line or "").strip())
    body = _e(page.get("body"))
    image = page.get("image") or {}
    image_html = _render_image_frame(image, page=page, mode=page.get("mode", "editorial"), fig_label="FIG. 01", default_ratio="r-16x9")
    inner = f"""
      <div class="content stack gap-4">
        <div class="issue-row">
          <span>{_e(page.get("kicker", "Issue 01"))}</span><span class="dot"></span><span>Chora</span>
        </div>
        <div class="stack gap-2">
          <p class="kicker">Cover · Rednote</p>
          <h1 class="h-display"{_title_style("".join(title_lines), base_px=92, page=page)}>{title}</h1>
          <p class="h-sub">{_e(page.get("source_title", "Editorial Card Set"))}</p>
        </div>
{image_html}
        <div class="callout">
          {body}
          <span class="callout-src">Swipe for the argument</span>
        </div>
      </div>"""
    return _editorial_shell(page, inner)


def _render_field_note_photo(page: dict) -> str:
    image = page.get("image") or {}
    if not image.get("src"):
        return _render_marginalia(page)
    paragraphs = _paragraphs(page.get("body", ""), limit=3)
    lead = page.get("subhead") or (paragraphs[0] if paragraphs else page.get("body", ""))
    note = page.get("pullquote", "")
    image_html = _render_image_frame(image, page=page, mode=page.get("mode", "editorial"), fig_label=f"FIELD {_display_number(page)}", default_ratio="r-3x4")
    inner = f"""
      <div class="content stack gap-3">
        <div class="issue-row">
          <span>{_e(page.get("kicker", "Field Note"))}</span><span class="dot"></span><span>Photo Evidence</span>
        </div>
        <div style="display:grid;grid-template-columns:5fr 4fr;gap:42px;align-items:stretch;min-height:960px">
          <div style="display:flex;flex-direction:column;justify-content:space-between">
            <div class="stack gap-3">
              <h2 class="h-xl"{_title_style(_title_plain(page), base_px=76, page=page)}>{_title_html(page, accent=True)}</h2>
              <p class="lead" style="font-size:34px;line-height:1.42">{_e(lead)}</p>
            </div>
            {f'<div class="callout" style="font-size:28px;line-height:1.35">{_e(note)}<span class="callout-src">field note · {_display_number(page)}</span></div>' if note else ''}
          </div>
{image_html}
        </div>
      </div>"""
    return _editorial_shell(page, inner)


def _render_evidence_feature(page: dict) -> str:
    paragraphs = _paragraphs(page.get("body", ""), limit=5)
    lead = page.get("subhead") or (paragraphs[0] if paragraphs else page.get("body", ""))
    image = page.get("image") or {}
    image_html = _render_image_frame(image, page=page, mode=page.get("mode", "editorial"), fig_label=f"FIG. {str(page.get('id', 'xhs-02'))[-2:]}", default_ratio="r-4x3")
    detail_items = _labelled_items(paragraphs[1:] or page.get("points", []), exclude=[lead], limit=3)
    rows = "\n".join(
        f"""
          <div class="ledger-row">
            <div class="ledger-nb">{_e(item.get("index", ""))}</div>
            <div>
              <div class="ledger-title">{_e(_item_primary(item))}</div>
              <div class="ledger-note">{_e(_item_secondary(item))}</div>
            </div>
          </div>"""
        for item in detail_items
    )
    ledger_html = f"""
        <div class="ledger">
{rows}
        </div>""" if rows else ""
    callout_text = page.get("pullquote", "")
    source_band = "" if rows or not callout_text else f"""
        <div class="callout" style="font-size:28px;line-height:1.25">
          {_e(callout_text)}
          <span class="callout-src">{_e(page.get("kicker", "Evidence"))}</span>
        </div>"""
    inner = f"""
      <div class="content stack gap-3">
        <p class="kicker">{_e(page.get("kicker", "Evidence"))} · Evidence</p>
        <h2 class="h-xl"{_title_style(_title_plain(page), base_px=72, page=page)}>{_title_html(page, accent=True)}</h2>
        <p class="lead">{_e(lead)}</p>
{image_html}
{ledger_html}
{source_band}
      </div>"""
    return _editorial_shell(page, inner)


def _render_checklist(page: dict) -> str:
    items = _page_items(page, limit=6)
    rows = "\n".join(
        f"""
          <div class="ledger-row" style="min-height:118px;align-items:start">
            <div class="ledger-nb">{_e(item.get("index", f"{index:02d}"))}</div>
            <div>
              <div class="ledger-title">{_e(_item_primary(item))}</div>
              <div class="ledger-note">{_e(_item_secondary(item))}</div>
            </div>
          </div>"""
        for index, item in enumerate(items[:6], start=1)
    )
    image_html = _render_image_frame(page.get("image") or {}, page=page, mode=page.get("mode", "editorial"), fig_label="MATERIAL", default_ratio="r-16x9")
    inner = f"""
      <div class="content stack gap-3">
        <p class="kicker">{_e(page.get("kicker", "Checklist"))} · Checklist</p>
        <h2 class="h-xl"{_title_style(_title_plain(page), base_px=78, page=page)}>{_title_html(page, accent=True)}</h2>
        <div class="ledger" style="min-height:680px;justify-content:space-between">
{rows}
        </div>
{image_html}
      </div>"""
    return _editorial_shell(page, inner)


def _render_evidence_wall(page: dict) -> str:
    images = page.get("images") or []
    if not images and page.get("image"):
        images = [page.get("image")]
    if len(images) < 2:
        return _render_evidence_feature(page)
    cells = "\n".join(
        f"""
          <figure class="frame-img r-4x3" style="min-height:270px">
            <img src="{_e(image.get("src"))}" alt="{_e(image.get("caption") or image.get("asset_id") or "Evidence")}" style="object-position:{_e(image.get("object_position", "center 50%"))}">
            <figcaption class="img-cap">E{index:02d} · {_e(image.get("caption") or image.get("asset_id") or "Evidence")}</figcaption>
          </figure>"""
        for index, image in enumerate(images[:4], start=1)
        if image.get("src")
    )
    items = _page_items(page, limit=3)
    notes = "\n".join(
        f"""
            <div style="border-top:1px solid var(--line);padding-top:14px">
              <span style="display:block;font-family:var(--mono);font-size:18px;letter-spacing:.12em;color:var(--accent)">{_e(item.get("index"))}</span>
              <span style="display:block;margin-top:8px;font-family:var(--serif-zh);font-size:28px;line-height:1.24;color:var(--ink)">{_e(_item_primary(item))}</span>
            </div>"""
        for item in items
    )
    inner = f"""
      <div class="content stack gap-3">
        <p class="kicker">{_e(page.get("kicker", "Evidence Wall"))} · Evidence Wall</p>
        <h2 class="h-xl"{_title_style(_title_plain(page), base_px=76, page=page)}>{_title_html(page, accent=True)}</h2>
        <div style="display:grid;grid-template-columns:2fr 1fr;gap:34px;align-items:stretch">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:22px">
{cells}
          </div>
          <div style="border-left:1px solid var(--line);padding-left:26px;display:flex;flex-direction:column;justify-content:space-between">
            <p class="lead" style="font-size:30px;line-height:1.42">{_e(page.get("body"))}</p>
            <div style="display:grid;gap:22px">
{notes}
            </div>
          </div>
        </div>
      </div>"""
    return _editorial_shell(page, inner)


def _render_editorial_essay(page: dict) -> str:
    paragraphs = _paragraphs(page.get("body", ""), limit=5)
    lead = paragraphs[0] if paragraphs else page.get("body", "")
    body_parts = _without_repeats(paragraphs[1:], exclude=[lead], limit=4)
    paragraph_html = "\n".join(f'          <p class="body">{_e(part)}</p>' for part in body_parts)
    density_html = (
        _density_panel(page, label="Insight Field", min_height=420, exclude=[lead, *body_parts])
        if _is_sparse_body(page)
        else ""
    )
    if paragraph_html:
        body_html = f"""
        <div class="col-2">
          <p class="lead">{_e(lead)}</p>
          <div>
{paragraph_html}
          </div>
        </div>"""
    else:
        body_html = f"""
        <p class="lead">{_e(lead)}</p>"""
    inner = f"""
      <div class="content stack gap-3">
        <p class="kicker">{_e(page.get("kicker", "Insight"))}</p>
        <h2 class="h-xl"{_title_style(_title_plain(page), base_px=82, page=page)}>{_title_html(page, accent=True)}</h2>
        <hr class="rule-accent">
{body_html}
{density_html}
      </div>"""
    return _editorial_shell(page, inner)


def _render_section_divider(page: dict) -> str:
    title = page.get("section_title") or page.get("title", "")
    subtitle = page.get("subtitle") or page.get("body") or page.get("reader_takeaway", "")
    inner = f"""
      <div class="content stack gap-4" style="justify-content:center;align-items:flex-start">
        <p class="kicker">{_e(page.get("kicker", "Act II · Part 2"))}</p>
        <h1 class="h-display"{_title_style(title, base_px=108)}>{_title_html_from_text(title, target=12, max_lines=3, accent=True)}</h1>
        <p class="h-sub" style="max-width:760px">{_e(subtitle)}</p>
        <hr class="rule-accent" style="width:220px;height:4px">
      </div>"""
    return _editorial_shell(page, inner)


def _render_editorial_quote(page: dict) -> str:
    lead = _paragraphs(page.get("body", ""), limit=3)
    quote = " ".join(lead) if lead else page.get("title", "")
    inner = f"""
      <div class="content stack gap-3" style="justify-content:center">
        <p class="kicker">{_e(page.get("kicker", "Thesis"))}</p>
        <p class="pullquote">{_e(quote)}</p>
        <hr class="rule">
        <p class="lead">{_e(page.get("title"))}</p>
      </div>"""
    return _editorial_shell(page, inner)


def _before_after_blocks(page: dict) -> tuple[dict, dict]:
    comparison = page.get("comparison") or {}
    if comparison.get("before") and comparison.get("after"):
        return comparison["before"], comparison["after"]
    source_title = page.get("original_title") or page.get("title", "")
    match = re.search(r"不是(.+?)，而是(.+?)[。.!！?？]?$", str(source_title or ""))
    if match:
        before_title = match.group(1).strip()
        after_title = match.group(2).strip()
        points = _paragraphs(page.get("body", ""), limit=6)
        # 单句 body 时，before 用否定原判断，after 用原句，避免重复
        if len(points) == 1:
            single = points[0]
            return (
                {"kicker": "Before · 误判", "title": before_title, "bullets": [f"问题不在{before_title}。"]},
                {"kicker": "After · 真因", "title": after_title, "bullets": [single]},
            )
        mid = max(1, len(points) // 2)
        return (
            {
                "kicker": "Before · 误判",
                "title": before_title,
                "bullets": points[:mid] or [f"问题不在{before_title}。"],
            },
            {
                "kicker": "After · 真因",
                "title": after_title,
                "bullets": points[mid:] or [f"真正变量是{after_title}。"],
            },
        )
    items = _page_items(page, limit=6)
    mid = max(1, len(items) // 2)
    before_items = items[:mid]
    after_items = items[mid:] or items[:1]
    # 单条目或全部相同时，用 title 做 before，body 做 after，避免同句重复
    if len(items) == 1 or all(_item_primary(i) == _item_primary(items[0]) for i in items):
        return (
            {
                "kicker": "Before · 旧",
                "title": "",
                "bullets": [str(page.get("title", "")).strip().rstrip("。！？；;") + "。"] if page.get("title") else [_item_primary(items[0])],
            },
            {
                "kicker": "After · 新",
                "title": "",
                "bullets": [_item_secondary(items[0]) or _item_primary(items[0])],
            },
        )
    return (
        {
            "kicker": "Before · 旧",
            "title": _item_title(before_items[0]),
            "bullets": [_item_secondary(item) or _item_primary(item) for item in before_items[:4]],
        },
        {
            "kicker": "After · 新",
            "title": _item_title(after_items[0]),
            "bullets": [_item_secondary(item) or _item_primary(item) for item in after_items[:4]],
        },
    )


def _bullet_list(items: list[str]) -> str:
    bullets = "\n".join(f"              <li>{_e(item)}</li>" for item in items if str(item or "").strip())
    return f"""
            <ul class="body" style="margin:0;padding-left:1.2em;font-size:28px;line-height:1.55">
{bullets}
            </ul>"""


def _render_before_after(page: dict) -> str:
    before, after = _before_after_blocks(page)
    before_title = f'            <h3 class="h-md">{_e(before.get("title"))}</h3>' if before.get("title") else ""
    after_title = f'            <h3 class="h-md">{_e(after.get("title"))}</h3>' if after.get("title") else ""
    inner = f"""
      <div class="content stack gap-3">
        <p class="kicker">{_e(page.get("kicker", "Before · After"))}</p>
        <h2 class="h-xl"{_title_style(_title_plain(page), base_px=78, page=page)}>{_title_html(page, accent=True)}</h2>
        <div class="beforeafter" style="min-height:760px">
          <div class="ba-block before">
            <p class="kicker">{_e(before.get("kicker", "Before · 旧"))}</p>
{before_title}
{_bullet_list(before.get("bullets") or [])}
          </div>
          <div class="ba-block">
            <p class="kicker">{_e(after.get("kicker", "After · 新"))}</p>
{after_title}
{_bullet_list(after.get("bullets") or [])}
          </div>
        </div>
      </div>"""
    return _editorial_shell(page, inner)


def _render_image_led_cover(page: dict) -> str:
    image = page.get("image") or {}
    subject_map = page.get("subject_map") or image.get("subject_map")
    if not image.get("src") or not subject_map:
        return _render_editorial_cover(page)
    title_lines = page.get("title_lines") or [page.get("title")]
    title = "<br>".join(_e(line) for line in title_lines if str(line or "").strip())
    body = page.get("body") or page.get("reader_takeaway") or ""
    safe_zone = _e(subject_map.get("safe_zone", "top and bottom quiet bands"))
    focus = _e(subject_map.get("focus", "primary subject in middle third"))
    object_position = image.get("object_position", "center 50%")
    return f"""
    <section class="poster xhs" id="{_e(page.get("id"))}" {_section_attrs(page)}>
      <!-- subject map:
           focus: {focus}
           safe text zone: {safe_zone}
           quiet-zone test: {_e(subject_map.get("quiet_zone", "required"))}
           light test: {_e(subject_map.get("light", "required"))}
           thumbnail policy: verify 360px title readability; if needed, use localized image-toned tint only.
      -->
      <div class="hero-bleed" style="background-image:url('{_e(image.get("src"))}');background-size:cover;background-position:{_e(object_position)};position:absolute;inset:0"></div>
      <div class="content" style="position:relative;height:100%;color:#f5f1e8;padding:72px 80px;display:flex;flex-direction:column;z-index:1">
        <p class="kicker" style="color:#f5f1e8;opacity:.86;font-family:var(--mono);font-size:22px;letter-spacing:.22em;text-transform:uppercase;margin:0">{_e(page.get("kicker", "Cover · Image Led"))}</p>
        <div style="flex:1"></div>
        <h1 style="font-family:var(--serif-zh);font-weight:500;font-size:62px;line-height:1.18;letter-spacing:.04em;color:#f5f1e8;margin:0 0 18px;max-width:100%;overflow-wrap:break-word;word-break:keep-all">{title}</h1>
        <div style="border-top:1px solid rgba(245,241,232,.35);padding-top:14px;font-family:var(--mono);font-size:19px;letter-spacing:.22em;text-transform:uppercase;color:#f5f1e8;opacity:.86">
          {_e(body)}
        </div>
      </div>
    </section>"""


def _render_atmospheric_thesis(page: dict) -> str:
    paragraphs = _paragraphs(page.get("body", ""), limit=2)
    lead = " ".join(paragraphs) if paragraphs else page.get("body", "")
    number = _display_number(page)
    details = _density_items(page, limit=3, exclude=[page.get("title", ""), lead, page.get("pullquote", "")])
    detail_html = "\n".join(
        f'<div style="border-top:1px solid var(--line);padding-top:12px"><span style="font-family:var(--mono);font-size:16px;color:var(--accent);letter-spacing:.12em">{_e(item.get("index"))}</span><p style="margin-top:8px;font-family:var(--serif-zh);font-size:22px;line-height:1.42;color:var(--ink)">{_e(_item_primary(item))}</p></div>'
        for item in details
    )
    callout = page.get("pullquote") or _slot_text(page, "caption")
    inner = f"""
      <div class="content stack gap-4" style="justify-content:space-between">
        <div class="issue-row">
          <span>{_e(page.get("kicker", "Thesis"))}</span><span class="dot"></span><span>Point {number}</span>
        </div>
        <div style="position:absolute;right:72px;top:128px;font-family:var(--mono);font-size:220px;line-height:.8;color:rgba(var(--accent-rgb),.14);letter-spacing:0">{_e(number)}</div>
        <div class="stack gap-3" style="position:relative;z-index:1">
          <h2 class="h-display"{_title_style(_title_plain(page, target=12), base_px=82, page=page)}>{_title_html(page, target=12, accent=True)}</h2>
          <hr class="rule-accent" style="width:180px;height:4px">
          {f'<p class="lead" style="max-width:760px">{_e(lead)}</p>' if lead else ''}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;position:relative;z-index:1">{detail_html}</div>
        {f'<div class="callout" style="font-size:30px;line-height:1.36;max-width:820px">{_e(callout)}<span class="callout-src">核心判断 · {number}</span></div>' if callout else ''}
      </div>"""
    return _editorial_shell(page, inner)


def _render_hero_question(page: dict) -> str:
    paragraphs = _paragraphs(page.get("body", ""), limit=3)
    body = " ".join(paragraphs)
    inner = f"""
      <div class="content stack gap-4" style="justify-content:space-between">
        <div class="stack gap-3">
          <p class="kicker">{_e(page.get("kicker", "The Question"))}</p>
          <div style="width:160px;height:10px;background:var(--accent);margin-bottom:8px"></div>
          <h1 class="h-display"{_title_style(_title_plain(page, target=12), base_px=104, page=page)}>{_title_html(page, target=12, accent=True)}</h1>
          <p class="lead" style="font-size:26px;line-height:1.62;max-height:340px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:6;-webkit-box-orient:vertical">{_e(body)}</p>
          <hr class="rule">
          <p class="kicker" style="font-size:18px">What remains after the argument.</p>
        </div>
{_density_panel(page, label="Epilogue Field", min_height=360, exclude=[body])}
      </div>"""
    return _editorial_shell(page, inner)


def _render_ledger(page: dict) -> str:
    if page.get("role") == "closing":
        return _render_closing_note(page)

    items = _page_items(page, limit=5)
    rows = "\n".join(
        f"""
          <div class="ledger-row">
            <div class="ledger-nb">{_e(item.get("index", ""))}</div>
            <div>
              <div class="ledger-title">{_e(_item_primary(item))}</div>
              <div class="ledger-note">{_e(_item_secondary(item))}</div>
            </div>
          </div>"""
        for item in items[:5]
    )
    needs_density = len(items) <= 4 or page.get("role") == "closing"
    density_exclude = [_item_primary(item) for item in items] + [_item_secondary(item) for item in items]
    ledger_min_height = 520 if needs_density else 620
    inner = f"""
      <div class="content stack gap-3">
        <p class="kicker">{_e(page.get("kicker", "Ledger"))}</p>
        <h2 class="h-xl"{_title_style(_title_plain(page), base_px=78, page=page)}>{_title_html(page, accent=True)}</h2>
        <div class="ledger" style="min-height:{ledger_min_height}px;justify-content:space-between">
{rows}
        </div>
{_density_panel(page, label="Ledger Field", min_height=320, exclude=density_exclude) if needs_density else ""}
      </div>"""
    return _editorial_shell(page, inner)


def _render_sparse_marginalia(page: dict) -> str:
    paragraphs = _paragraphs(page.get("body", ""), limit=4)
    pullquote = str(page.get("pullquote") or "").strip()
    body_html = "\n".join(
        f'              <p style="margin:0 0 22px;font-family:var(--serif-zh);font-size:36px;line-height:1.54;color:var(--ink)">{_e(part)}</p>'
        for part in paragraphs
    )
    tags = "\n".join(
        f"""
              <div style="border-top:1px solid var(--line);padding-top:14px">
                <span style="display:block;font-family:var(--mono);font-size:18px;letter-spacing:.12em;color:var(--accent)">{_e(item.get("index"))}</span>
                <span style="display:block;margin-top:8px;font-family:var(--serif-zh);font-size:32px;color:var(--ink)">{_e(_item_primary(item))}</span>
              </div>"""
        for item in _density_items(page, exclude=paragraphs)
    )
    number = _display_number(page)
    inner = f"""
      <div class="content stack gap-4" style="justify-content:space-between">
        <div class="stack gap-3">
          <p class="kicker">{_e(page.get("kicker", "Marginalia"))}</p>
          <h2 class="h-xl"{_title_style(_title_plain(page), base_px=84, page=page)}>{_title_html(page, accent=True)}</h2>
        </div>
        <div class="sparse-thesis" style="display:grid;grid-template-columns:7fr 3fr;gap:44px;align-items:stretch">
          <div style="min-height:500px;background:var(--paper-2);border-left:4px solid var(--accent);padding:42px 46px;display:flex;flex-direction:column;justify-content:center">
{body_html}
            {f'<div class="callout" style="font-size:28px;line-height:1.35;margin-top:20px">{_e(pullquote)}<span class="callout-src">核心判断 · {number}</span></div>' if pullquote else '<span style="font-family:var(--mono);font-size:20px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">body as argument</span>'}
          </div>
          <div style="position:relative;border-left:1px solid var(--line);padding-left:28px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden">
            <div style="font-family:var(--mono);font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">Margin Notes</div>
            <div style="font-family:var(--mono);font-size:190px;line-height:.82;letter-spacing:0;color:rgba(var(--accent-rgb),.22)">{_e(number)}</div>
            <div style="display:grid;grid-template-columns:1fr;gap:22px">
{tags}
            </div>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:18px;font-family:var(--mono);font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">
          <span>Chora note</span>
          <span>Point {number}</span>
        </div>
      </div>"""
    return _editorial_shell(page, inner)


def _render_marginalia(page: dict) -> str:
    if _is_sparse_body(page, threshold=170):
        return _render_sparse_marginalia(page)

    paragraphs = _paragraphs(page.get("body", ""), limit=5)
    body_html = "\n".join(f'            <p class="body">{_e(part)}</p>' for part in paragraphs)
    notes = "\n".join(f"            <p>{_e(_item_primary(item))}</p>" for item in _labelled_items(paragraphs, limit=5))
    inner = f"""
      <div class="content stack gap-3">
        <p class="kicker">{_e(page.get("kicker", "Marginalia"))}</p>
        <h2 class="h-xl"{_title_style(_title_plain(page), base_px=78, page=page)}>{_title_html(page, accent=True)}</h2>
        <div class="marginalia">
          <div>
{body_html}
          </div>
          <div class="mg-col">
{notes}
          </div>
        </div>
      </div>"""
    return _editorial_shell(page, inner)


def _render_closing_note(page: dict) -> str:
    items = (page.get("items") or [])[:3]
    item_html = "\n".join(
        f"""
          <div style="border-top:1px solid var(--line);padding-top:18px">
            <div style="font-family:var(--mono);font-size:22px;letter-spacing:.1em;color:var(--accent)">{_e(item.get("index", ""))}</div>
            <div style="margin-top:14px;font-family:var(--serif-zh);font-size:30px;line-height:1.18;color:var(--ink)">{_e(_item_primary(item))}</div>
          </div>"""
        for item in items
    )
    inner = f"""
      <div class="content stack gap-4" style="justify-content:space-between">
        <div class="stack gap-3">
          <p class="kicker">{_e(page.get("kicker", "Closing Note"))}</p>
          <h1 class="h-display"{_title_style(_title_plain_from_text(page.get("title", ""), target=8), base_px=82)}>{_title_html_from_text(page.get("title", ""), target=8, accent=True)}</h1>
          <p class="lead" style="font-size:34px;line-height:1.48;max-width:780px">{_e(page.get("body"))}</p>
        </div>
        <div class="closing-mark" style="position:relative;min-height:420px;background:var(--paper-2);border:1px solid var(--line);padding:36px 40px;overflow:hidden">
          <div style="position:absolute;right:34px;bottom:-28px;font-family:var(--serif-en);font-size:156px;line-height:.9;color:rgba(var(--accent-rgb),.16);letter-spacing:0">Chora</div>
          <div style="position:relative;z-index:1;display:flex;justify-content:space-between;font-family:var(--mono);font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">
            <span>read the full issue</span>
            <span>{_e(page.get("id", ""))}</span>
          </div>
          <div style="position:relative;z-index:1;margin-top:118px;display:grid;grid-template-columns:repeat(3,1fr);gap:28px">
{item_html}
          </div>
        </div>
{_cta_strip(page)}
      </div>"""
    return _editorial_shell(page, inner)


def _render_pipeline(page: dict) -> str:
    if not page.get("items"):
        return _render_structure_prose(page)

    items = page.get("items")
    if not items:
        items = [{"index": "01", "title": page.get("title", ""), "note": page.get("body", "")}]
    steps = "\n".join(
        f"""
          <div class="step">
            <div class="step-nb">{_e(item.get("index", ""))}</div>
            <div>
              <h3 class="step-title">{_e(_item_primary(item))}</h3>
              <p class="step-desc">{_e(_item_secondary(item))}</p>
            </div>
          </div>"""
        for item in items[:5]
    )
    inner = f"""
      <div class="content stack gap-3">
        <p class="kicker">{_e(page.get("kicker", "Structure"))}</p>
        <h2 class="h-xl"{_title_style(_title_plain(page), base_px=78, page=page)}>{_title_html(page, accent=True)}</h2>
        <div class="pipeline-v" style="min-height:430px;justify-content:space-between">
{steps}
        </div>
{_density_panel(page, label="Structure Field", min_height=420) if len(items) < 4 or _is_sparse_body(page, threshold=180) else ""}
      </div>"""
    return _editorial_shell(page, inner)


def _render_structure_prose(page: dict) -> str:
    paragraphs = _paragraphs(page.get("body", ""), limit=4)
    body_html = "\n".join(
        f'            <p style="margin:0 0 24px;font-family:var(--serif-zh);font-size:34px;line-height:1.55;color:var(--ink)">{_e(part)}</p>'
        for part in paragraphs
    )
    number = _display_number(page)
    inner = f"""
      <div class="content stack gap-4" style="justify-content:space-between">
        <div class="stack gap-3">
          <p class="kicker">{_e(page.get("kicker", "Structure"))}</p>
          <h2 class="h-xl"{_title_style(_title_plain(page), base_px=82, page=page)}>{_title_html(page, accent=True)}</h2>
        </div>
        <div class="structure-prose" style="display:grid;grid-template-columns:7fr 3fr;gap:44px;align-items:stretch">
          <div style="min-height:520px;background:var(--paper-2);border-left:4px solid var(--accent);padding:46px 50px;display:flex;flex-direction:column;justify-content:center">
{body_html}
            <span style="font-family:var(--mono);font-size:20px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">continuous reading</span>
          </div>
          <div style="border-left:1px solid var(--line);padding-left:30px;display:flex;flex-direction:column;justify-content:space-between">
            <div style="font-family:var(--mono);font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">Point {number}</div>
            <div style="font-family:var(--mono);font-size:190px;line-height:.82;letter-spacing:0;color:rgba(var(--accent-rgb),.22)">{_e(number)}</div>
            <div style="font-family:var(--serif-zh);font-size:30px;line-height:1.28;color:var(--accent)">流动<br>回路<br>交换</div>
          </div>
        </div>
        <div style="display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:18px;font-family:var(--mono);font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)">
          <span>Chora note</span>
          <span>no forced taxonomy</span>
        </div>
      </div>"""
    return _editorial_shell(page, inner)


def _swiss_shell(page: dict, inner: str, mat_class: str = "") -> str:
    mat = f'\n      <div class="{_e(mat_class)}"></div>' if mat_class else ""
    return f"""
    <section class="poster xhs" id="{_e(page.get("id"))}" {_section_attrs(page)}>
{mat}
{inner}
    </section>"""


def _swiss_title_lines(title: str, max_lines: int = 2) -> str:
    return "<br>".join(_e(line) for line in semantic_title_lines(str(title or ""), target=9, max_lines=max_lines, min_tail=3))


def _swiss_header(page: dict, right: str | None = None) -> str:
    return f"""
        <div class="chrome-min">
          <span>{_e(page.get("kicker", "Issue"))}</span>
          <span>{_e(right or page.get("id", ""))}</span>
        </div>"""


def _swiss_evidence_panel(page: dict, label: str = "Evidence", min_height: int = 360) -> str:
    image = page.get("image") or {}
    if not image.get("src"):
        return ""
    caption = _image_caption_label(image.get("caption") or image.get("asset_id") or label)
    return f"""
        <figure class="frame-img r-4x3" style="margin:0;min-height:{min_height}px;background:var(--white);border:1px solid var(--grey-2);display:grid;grid-template-rows:1fr auto;overflow:hidden">
          <div style="min-height:0;display:flex;align-items:center;justify-content:center;padding:var(--sp-4)">
            <img src="{_e(image.get("src"))}" alt="{_e(caption)}" style="width:100%;height:100%;object-fit:contain;object-position:{_e(image.get("object_position", "center 50%"))}">
          </div>
          <figcaption class="t-meta" style="padding:var(--sp-4);border-top:1px solid var(--grey-2);color:var(--grey-4)">{_e(label)} · {_e(caption)}</figcaption>
        </figure>"""


def _swiss_items(page: dict, limit: int = 4) -> list[dict]:
    items = _page_items(page, limit=limit)
    if items:
        return items[:limit]
    points = page.get("points") or _paragraphs(page.get("body", ""), limit=limit)
    return _labelled_items(points, limit=limit)


def _swiss_body_lines(page: dict, limit: int = 3) -> list[str]:
    lines = _paragraphs(page.get("body", ""), limit=limit)
    if lines:
        return lines
    return [_item_secondary(item) or _item_primary(item) for item in _swiss_items(page, limit=limit)]


def _swiss_metric_rows(page: dict, limit: int = 4, items: list[dict] | None = None) -> list[dict]:
    tokens = page.get("metric_tokens") or []
    rows = []
    for index, item in enumerate((items or _swiss_items(page, limit=limit))[:limit], start=1):
        title = _item_title(item)
        note = _item_note(item)
        label = title or note or f"Point {index:02d}"
        if not title:
            note = ""
        value = item.get("value")
        display_value = item.get("display_value")
        source = item.get("metric_source")
        if index <= len(tokens):
            token = tokens[index - 1]
            value = token.get("value", value)
            display_value = token.get("raw") or display_value
            source = token.get("source", "extracted")
        if value is None:
            value = len(_norm_text(f"{label}{note}"))
        if not source:
            source = "proxy"
        if not display_value:
            display_value = str(value) if source == "extracted" else f"rank {index:02d}"
        rows.append(
            {
                "index": f"{index:02d}",
                "label": label,
                "note": note,
                "value": value,
                "display_value": display_value,
                "source": source,
            }
        )
    if rows:
        return rows[:limit]
    return [{"index": "01", "label": page.get("title", "Signal"), "note": page.get("body", ""), "value": 1}]


def _swiss_stats(page: dict, limit: int = 4) -> list[dict]:
    stats = page.get("stats") or []
    if stats:
        return stats[:limit]
    points = page.get("points") or _paragraphs(page.get("body", ""), limit=4)
    chips = page.get("chips") or []
    return [
        {"num": str(len(points) or 1), "lbl": "ARGUMENTS", "height": 260},
        {"num": str(page.get("display_index") or "01"), "lbl": "POINT", "height": 220},
        {"num": str(len(chips) or 3), "lbl": "SIGNALS", "height": 180},
        {"num": str(len(_norm_text(page.get("title", ""))) or 1), "lbl": "TITLE", "height": 140, "muted": True},
    ][:limit]


def _render_swiss_accent_cover(page: dict) -> str:
    lines = page.get("title_lines")
    title = "<br>".join(_e(line) for line in lines) if lines else _swiss_title_lines(page.get("title"))
    evidence = _swiss_evidence_panel(page, label="Source", min_height=360)
    right_block = evidence or f"""
          <div class="card-outlined" style="display:flex;flex-direction:column;justify-content:space-between">
            <p class="t-meta">CHORA</p>
            <p class="lead">{_e(page.get("body"))}</p>
          </div>"""
    inner = f"""
      <div class="content stack gap-9">
{_swiss_header(page, right=page.get("source_title", page.get("id", "")))}
        <div class="stack gap-7">
          <p class="t-cat">Cover · Rednote</p>
          <h1 class="h-statement" style="font-size:84px;line-height:1.08">{title}</h1>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-7);min-height:360px">
          <div class="card-accent" style="display:flex;flex-direction:column;justify-content:space-between">
            <p class="t-cat">SYSTEM</p>
            <p class="num-xl">{_e(page.get("display_index", "01"))}</p>
          </div>
{right_block}
        </div>
        <div class="grow"></div>
        <hr class="hr-accent">
        <p class="t-meta">{_e(page.get("footer", "Chora · Rhizomata"))}</p>
      </div>
"""
    return _swiss_shell(page, inner, mat_class="dot-mat")


def _render_swiss_two_signals(page: dict) -> str:
    before, after = _before_after_blocks(page)
    before_title = f'            <h3 class="h-md">{_e(before.get("title"))}</h3>' if before.get("title") else ""
    after_title = f'            <h3 class="h-md">{_e(after.get("title"))}</h3>' if after.get("title") else ""
    evidence = _swiss_evidence_panel(page, min_height=430)
    grid_min_height = 520 if evidence else 720
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Two Signals · Comparison</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
{evidence}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-7);min-height:{grid_min_height}px">
          <div class="card-ink" style="display:flex;flex-direction:column;justify-content:space-between">
            <p class="t-cat">{_e(before.get("kicker", "Signal A"))}</p>
{before_title}
            <p class="body">{_e(" ".join(before.get("bullets") or []))}</p>
          </div>
          <div class="card-outlined" style="display:flex;flex-direction:column;justify-content:space-between">
            <p class="t-cat">{_e(after.get("kicker", "Signal B"))}</p>
{after_title}
            <p class="body">{_e(" ".join(after.get("bullets") or []))}</p>
          </div>
        </div>
        <p class="t-meta">{_e(_slot_text(page, "meta", page.get("footer", "")))}</p>
      </div>"""
    return _swiss_shell(page, inner)


def _render_swiss_file_card(page: dict) -> str:
    props = _swiss_metric_rows(page, limit=4, items=_slot_items(page, "sentences", limit=4))
    chips = _visible_chips(page)
    evidence = _swiss_evidence_panel(page, min_height=360)
    rows = "\n".join(
        f"""
          <div style="display:grid;grid-template-columns:160px 1fr;gap:var(--sp-6);padding:var(--sp-6) 0;border-bottom:1px solid var(--grey-2)">
            <p class="t-meta">{_e(item["index"])}</p>
            <div>
              <p class="lead">{_e(item["label"])}</p>
              <p class="body">{_e(item["note"])}</p>
            </div>
          </div>"""
        for item in props
    )
    chip_axis = "\n".join(
        f"""
              <div style="border-top:1px solid var(--grey-2);padding-top:var(--sp-4)">
                <p class="t-meta">{index:02d}</p>
                <p class="lead" style="font-size:28px;margin:0">{_e(chip.get("title", ""))}</p>
              </div>"""
        for index, chip in enumerate(chips[:3], start=1)
    )
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Data Layer · File Card</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
{evidence}
        <div class="card-fill" style="min-height:{'580' if evidence else '980'}px;display:grid;grid-template-rows:auto 1fr;gap:var(--sp-8)">
          <div style="display:flex;justify-content:space-between;align-items:start">
            <p class="num-mega">{_e(page.get("display_index", "01"))}</p>
            <p class="t-meta">SOURCE<br>OF<br>TRUTH</p>
          </div>
          <div style="display:flex;flex-direction:column;min-height:0">
            <div>
{rows}
            </div>
            <div style="margin-top:auto;display:grid;grid-template-columns:repeat(3,1fr);gap:var(--sp-5)">
{chip_axis}
            </div>
          </div>
        </div>
      </div>"""
    return _swiss_shell(page, inner)


def _render_swiss_interface_mock(page: dict) -> str:
    modules = _swiss_metric_rows(page, limit=3, items=_slot_items(page, "details", limit=3))
    if len(modules) < 3:
        for chip in _visible_chips(page)[: 3 - len(modules)]:
            modules.append(
                {
                    "index": f"{len(modules) + 1:02d}",
                    "label": chip.get("title", "Signal"),
                    "note": chip.get("note", ""),
                    "value": len(_norm_text(chip.get("title", ""))) or 1,
                    "display_value": f"rank {len(modules) + 1:02d}",
                    "source": "proxy",
                }
            )
    module_html = "\n".join(
        f"""
              <div class="card-fill" style="padding:var(--sp-6)">
                <p class="t-meta">{_e(item["index"])}</p>
                <p class="lead">{_e(item["label"])}</p>
              </div>"""
        for item in modules
    )
    trace_html = "\n".join(
        f"""
                <div style="border-top:1px solid var(--grey-2);padding-top:var(--sp-4)">
                  <p class="t-meta">{_e(item["index"])} · {_e(item.get("source", "proxy"))}</p>
                  <p class="body">{_e(item.get("display_value") or "signal slot")}</p>
                </div>"""
        for item in modules[:3]
    )
    image = page.get("image") or {}
    if image.get("src"):
        visual_block = f"""
              <div class="frame-shot" style="min-height:360px;background:var(--white);display:flex;align-items:center;justify-content:center;padding:var(--sp-5);border:1px solid var(--grey-2)">
                <img src="{_e(image.get("src"))}" alt="{_e(image.get("caption") or "evidence")}" style="width:100%;height:100%;object-fit:contain;object-position:{_e(image.get("object_position", "center 50%"))}">
              </div>"""
    else:
        visual_block = f"""
{module_html}"""
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Interface · Browser Mock</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
        <div class="device-browser" style="min-height:760px">
          <div class="frame-shot bg-grid inset-bal" style="min-height:720px">
            <div class="shot-body stack gap-6" style="min-height:620px;display:flex;flex-direction:column">
              <div class="card-ink">
                <p class="t-cat">OUTPUT</p>
                <p class="lead">{_e(_slot_text(page, "lead", page.get("body", "")))}</p>
              </div>
{visual_block}
              <div class="card-outlined" style="margin-top:auto;min-height:190px;padding:var(--sp-6);display:grid;grid-template-columns:140px 1fr;gap:var(--sp-6);align-items:start;background:rgba(255,255,255,.86)">
                <p class="num-xl" style="font-size:96px">{_e(page.get("display_index", "01"))}</p>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:var(--sp-5)">
{trace_html}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>"""
    return _swiss_shell(page, inner)


def _render_swiss_warning_rows(page: dict) -> str:
    row_items = _slot_items(page, "details", limit=3) or _slot_items(page, "sentences", limit=3)
    evidence = _swiss_evidence_panel(page, min_height=320)
    rows = "\n".join(
        f"""
          <div style="display:grid;grid-template-columns:150px 1fr;gap:var(--sp-7);padding:var(--sp-7) 0;border-bottom:1px solid var(--grey-2)">
            <p class="t-meta">RISK {index:02d}</p>
            <div>
              <p class="lead">{_e(_item_primary(item))}</p>
              <p class="body">{_e(_item_secondary(item))}</p>
            </div>
          </div>"""
        for index, item in enumerate(row_items, start=1)
    )
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Trap · Warning Rows</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
        <div class="card-accent">
          <p class="h-md">{_e(_slot_text(page, "lead", page.get("body", "")))}</p>
        </div>
{evidence}
        <div style="display:grid">
{rows}
        </div>
      </div>"""
    return _swiss_shell(page, inner, mat_class="dot-mat")


def _render_swiss_pipeline(page: dict) -> str:
    items = (page.get("items") or [])[:3] or _slot_items(page, "sentences", limit=3) or _swiss_items(page, limit=3)
    column_count = max(1, min(len(items), 3))
    grid_columns = f"repeat({column_count},minmax(0,1fr))"
    steps = "\n".join(
        f"""
          <div class="card-outlined" style="display:flex;flex-direction:column;justify-content:space-between;min-height:100%">
            <p class="num-xl">{index:02d}</p>
            <div>
              <p class="lead" style="font-size:38px;line-height:1.12">{_e(_item_primary(item))}</p>
              <p class="body">{_e(_item_secondary(item))}</p>
            </div>
          </div>"""
        for index, item in enumerate(items, start=1)
    )
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Pipeline · Architecture</p>
        <h2 class="h-xl">{_title_html(page, target=8, max_lines=3)}</h2>
        <div style="display:grid;grid-template-columns:{grid_columns};gap:var(--sp-6);min-height:640px;align-items:stretch">
{steps}
        </div>
        <p class="t-meta">{_e(_slot_text(page, "caption", page.get("footer", "")))}</p>
      </div>"""
    return _swiss_shell(page, inner, mat_class="cross-mat")


def _render_swiss_takeaway_ledger(page: dict) -> str:
    cta_marker = _swiss_cta_marker(page) if page.get("role") == "closing" else ""
    lead_text = _slot_text(page, "lead", page.get("body", ""))
    final_note = str(page.get("reader_takeaway") or "").strip()
    lead_norm = _norm_text(lead_text)
    final_norm = _norm_text(final_note)
    if not final_note or (lead_norm and final_norm and (lead_norm in final_norm or final_norm in lead_norm)):
        final_note = _slot_text(page, "caption", "把这一页当作回到全文的索引。")
    final_field = (
        _swiss_archive_mark(page)
        if cta_marker
        else f"""
          <div>
            <p class="t-meta">FINAL FIELD</p>
            <p class="lead" style="max-width:560px">{_e(final_note)}</p>
          </div>"""
    )
    card_grid = (
        "min-height:260px;display:grid;grid-template-columns:minmax(0,380px) 220px auto;align-items:center;gap:var(--sp-6)"
        if cta_marker
        else "min-height:260px;display:flex;align-items:center;justify-content:space-between"
    )
    row_items = (
        _swiss_items(page, limit=3)
        if page.get("role") == "closing"
        else (_slot_items(page, "details", limit=3) or _slot_items(page, "sentences", limit=3))
    )
    rows = "\n".join(
        f"""
          <div style="display:grid;grid-template-columns:160px 1fr;gap:var(--sp-7);padding:var(--sp-7) 0;border-top:1px solid var(--grey-2)">
            <p class="num-xl" style="font-size:88px">{_e(item.get("index", f"{index:02d}"))}</p>
            <div>
              <p class="lead">{_e(_item_primary(item))}</p>
              <p class="body">{_e(_item_secondary(item))}</p>
            </div>
          </div>"""
        for index, item in enumerate(row_items, start=1)
    )
    evidence = "" if page.get("role") == "closing" else _swiss_evidence_panel(page, min_height=320)
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Takeaway · Ledger</p>
        <h2 class="h-xl">{_title_html_from_text(page.get("title", ""), target=8, max_lines=2)}</h2>
        <p class="lead">{_e(lead_text)}</p>
        <div class="card-fill" style="{card_grid}">
{final_field}
{cta_marker}
          <p class="num-mega">{_e(page.get("display_index", "01"))}</p>
        </div>
{evidence}
        <div>
{rows}
        </div>
      </div>"""
    return _swiss_shell(page, inner, mat_class="ring-mat")


def _render_swiss_image_hero(page: dict) -> str:
    image = page.get("image") or {}
    subject_map = image.get("subject_map") or page.get("subject_map") or {}
    subject_comment = ""
    if subject_map:
        subject_comment = f"""
      <!-- subject map:
           focus: {_e(subject_map.get("focus", ""))}
           safe text zone: {_e(subject_map.get("safe_zone", ""))}
           quiet-zone test: {_e(subject_map.get("quiet_zone", ""))}
           light test: {_e(subject_map.get("light", ""))}
           thumbnail policy: verify 360px title readability; if needed, use localized image-toned tint only.
      -->"""
    stats = _swiss_stats(page, limit=3)
    stat_html = "\n".join(
        f"""
          <div class="stat-block" data-metric-source="{_e(stat.get("source", "proxy"))}">
            <p class="num">{_e(stat.get("num"))}</p>
            <p class="lbl">{_e(stat.get("lbl"))}</p>
          </div>"""
        for stat in stats
    )
    stat_html += f"""
          <div class="stat-block">
            <p class="num">{len(_norm_text(page.get("body", ""))) or 1}</p>
            <p class="lbl">WORDS</p>
          </div>"""
    if image.get("src"):
        hero_media = f'<img src="{_e(image.get("src"))}" alt="{_e(image.get("caption") or "hero")}" style="object-position:{_e(image.get("object_position", "center 35%"))}">'
    else:
        hero_media = """
        <div class="frame-shot bg-grid" style="width:100%;height:100%;display:flex;align-items:center;justify-content:center">
          <p class="num-mega">CH</p>
        </div>"""
    inner = f"""
{subject_comment}
      <div class="content stack gap-7">
{_swiss_header(page)}
        <div class="image-hero">
          <div class="hero-img-wrap">
{hero_media}
            <div class="hero-overlay-block">
              <p class="t-cat">Image Hero</p>
              <h1 class="h-statement" style="font-size:92px">{_title_html(page, target=9, max_lines=2)}</h1>
            </div>
          </div>
          <div class="hero-stats">
{stat_html}
          </div>
        </div>
        <p class="body">{_e(page.get("body"))}</p>
      </div>"""
    return _swiss_shell(page, inner, mat_class="dot-mat")


def _render_swiss_kpi_tower(page: dict) -> str:
    stats = _swiss_stats(page, limit=4)
    extracted_stats = [stat for stat in stats if stat.get("source") == "extracted"]
    body_lines = _copy_slots(page).get("sentences") or _swiss_body_lines(page, limit=4)
    argument_items = _labelled_items(body_lines, limit=4)
    metric_cards = "\n".join(
        f"""
          <div class="card-accent" data-metric-source="extracted" style="min-height:210px;padding:var(--sp-6);display:flex;flex-direction:column;justify-content:space-between">
            <p class="t-meta" style="margin:0;color:var(--accent-on);opacity:.72">{_e(stat.get("lbl", "EXTRACTED"))}</p>
            <p style="font-family:var(--sans);font-size:112px;font-weight:200;line-height:1;letter-spacing:-.02em;margin:0;color:var(--accent-on)">{_e(stat.get("num"))}</p>
          </div>"""
        for stat in extracted_stats[:2]
    )
    argument_cards = "\n".join(
        f"""
          <div class="card-fill" style="min-height:180px;padding:var(--sp-6);display:flex;flex-direction:column;justify-content:space-between">
            <p class="t-meta" style="margin:0;color:var(--grey-3)">{_e(item.get("index", f"{index:02d}"))}</p>
            <p class="body" style="margin:0;font-size:27px;line-height:1.38">{_e(_item_secondary(item) or _item_primary(item))}</p>
          </div>"""
        for index, item in enumerate(argument_items[: (2 if extracted_stats else 4)], start=1)
    )
    cols = metric_cards + argument_cards
    evidence = _swiss_evidence_panel(page, min_height=300)
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">KPI · Tower</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
        <div class="card-fill" style="padding:var(--sp-6);display:grid;grid-template-columns:180px 1fr;gap:var(--sp-7);align-items:start">
          <p class="t-meta">READING<br>FRAME</p>
          <p class="body">{_e(_slot_text(page, "caption", page.get("footer", "")))}</p>
        </div>
{evidence}
        <div class="kpi-tower-row" style="height:auto;grid-template-columns:repeat(2,1fr);gap:var(--sp-5);align-items:stretch">
{cols}
        </div>
      </div>"""
    return _swiss_shell(page, inner, mat_class="ring-mat")


def _render_swiss_hbar(page: dict) -> str:
    rows = _swiss_metric_rows(page, limit=6)
    max_value = max([int(row.get("value") or 1) for row in rows] or [1])
    row_html = "\n".join(
        f"""
          <div class="bar-row">
            <div class="row-lbl">{_e(row.get("label"))}</div>
            <div class="row-track"><div class="row-fill" style="--w:{max(16, round((int(row.get("value") or 1) / max_value) * 100))}%"></div></div>
            <div class="row-val" data-metric-source="{_e(row.get("source"))}">{_e(row.get("display_value"))}</div>
          </div>"""
        for row in rows
    )
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">H-Bar · Ranking</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
        <div class="h-bar-chart">
{row_html}
        </div>
      </div>"""
    return _swiss_shell(page, inner)


def _render_swiss_stacked_ledger(page: dict) -> str:
    icons = ["square-stack", "book-open", "bolt", "keyboard", "coffee", "layers"]
    items = _swiss_items(page, limit=5)
    rows = "\n".join(
        f"""
          <div class="ledger-row">
            <p class="ledger-num">{_e(item.get("index", f"{index:02d}"))}</p>
            <div class="ledger-lbl">{_e(_item_primary(item))}<span class="sub">{_e(_item_secondary(item))}</span></div>
            <i class="ledger-icn" data-lucide="{icons[(index - 1) % len(icons)]}"></i>
          </div>"""
        for index, item in enumerate(items, start=1)
    )
    # 增加底部 stat，填补最后一 band，改善 R5 密度
    stat_lead = _slot_text(page, "caption", page.get("footer", ""))
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Stacked · Ledger</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
        <div class="stacked-ledger">
{rows}
        </div>
        <div class="hero-stat-bottom">
          <div>
            <p class="t-cat">In total · 累计</p>
            <p class="lead">{_e(stat_lead)}</p>
          </div>
          <p class="num-mega">{len(items)}</p>
        </div>
      </div>"""
    return _swiss_shell(page, inner)


def _render_swiss_matrix(page: dict) -> str:
    cta_marker = _swiss_cta_marker(page) if page.get("role") == "closing" else ""
    archive_panel = (
        f"""
        <div class="card-fill" style="min-height:320px;display:grid;grid-template-columns:minmax(0,1fr) 260px;align-items:center;gap:var(--sp-8)">
{_swiss_archive_mark(page)}
{cta_marker}
        </div>"""
        if cta_marker
        else ""
    )
    closing_grow = '<div class="grow"></div>' if page.get("role") == "closing" else ""
    hero_stat_style = ""
    items = _slot_items(page, "sentences", limit=8) or _swiss_items(page, limit=8)
    matrix_style = ' style="grid-template-columns:1fr;grid-auto-rows:min-content"' if len(items) <= 3 else ""
    cell_min_height = 220 if len(items) <= 3 else 300 if len(items) <= 4 else 160
    cells = "\n".join(
        f"""
          <div class="matrix-cell{' is-accent' if index == 1 else ''}" style="min-height:{cell_min_height}px">
            <p class="cell-nb">{index:02d}</p>
            <p class="cell-title">{_e(_item_primary(item))}</p>
            <p class="body" style="font-size:24px;line-height:1.34;margin:0;color:{'var(--accent-on)' if index == 1 else 'var(--ink)'}">{_e(_item_secondary(item))}</p>
          </div>"""
        for index, item in enumerate(items, start=1)
    )
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Matrix · Hero Stat</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
        <div class="matrix-fill"{matrix_style}>
{cells}
        </div>
{archive_panel}
{closing_grow}
        <div class="hero-stat-bottom"{hero_stat_style}>
          <div>
            <p class="t-cat">In total · 累计</p>
            <p class="lead">{_e(_slot_text(page, "caption", page.get("footer", "")))}</p>
          </div>
          <p class="num-mega">{len(items)}</p>
        </div>
      </div>"""
    return _swiss_shell(page, inner)


def _render_swiss_map_route(page: dict) -> str:
    nodes = page.get("map_nodes") or []
    route = page.get("map_route") or {}
    origin = route.get("origin") or (nodes[0].get("label") if nodes else "A")
    destination = route.get("destination") or (nodes[-1].get("label") if nodes else "B")
    stops = route.get("stops") or [n.get("label") for n in nodes[1:-1]]
    # 构建抽象地图节点 HTML
    node_html = "\n".join(
        f"""
          <div class="map-node" style="display:flex;flex-direction:column;align-items:center;gap:10px">
            <div style="width:24px;height:24px;border-radius:50%;background:var(--accent);border:4px solid var(--white);box-shadow:0 0 0 2px var(--accent)"></div>
            <p class="t-meta" style="text-transform:none;letter-spacing:0">{_e(n.get('label', ''))}</p>
          </div>"""
        for n in nodes
    )
    route_line = """
          <div style="position:absolute;top:11px;left:0;right:0;height:2px;background:var(--accent);opacity:.4;z-index:0"></div>"""
    stops_html = " · ".join(_e(s) for s in stops) if stops else "直接连接"
    inner = f"""
      <div class="content stack gap-7">
{_swiss_header(page)}
        <p class="t-cat">Map · Route</p>
        <h2 class="h-xl">{_title_html(page, target=9, max_lines=2)}</h2>
        <p class="lead">{_e(_slot_text(page, "lead", page.get("body", "")))}</p>
        <div class="card-fill" style="min-height:520px;display:flex;flex-direction:column;justify-content:center;gap:var(--sp-8);padding:var(--sp-8)">
          <div style="position:relative;display:flex;justify-content:space-between;align-items:flex-start;padding:0 var(--sp-6)">
{route_line}
{node_html}
          </div>
          <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:var(--sp-6);align-items:center;margin-top:var(--sp-6)">
            <div style="text-align:right">
              <p class="t-meta">ORIGIN</p>
              <p class="lead" style="margin:0">{_e(origin)}</p>
            </div>
            <p class="t-cat" style="margin:0">→</p>
            <div>
              <p class="t-meta">DESTINATION</p>
              <p class="lead" style="margin:0">{_e(destination)}</p>
            </div>
          </div>
          <div style="border-top:1px solid var(--grey-2);padding-top:var(--sp-6);margin-top:auto">
            <p class="t-meta">STOPS</p>
            <p class="body">{_e(stops_html)}</p>
          </div>
        </div>
        <div class="hero-stat-bottom">
          <div>
            <p class="t-cat">In total · 累计</p>
            <p class="lead">{_e(_slot_text(page, "caption", page.get("footer", "")))}</p>
          </div>
          <p class="num-mega">{len(nodes)}</p>
        </div>
      </div>"""
    return _swiss_shell(page, inner)


SWISS_RENDERERS = {
    "S01": _render_swiss_accent_cover,
    "S02": _render_swiss_two_signals,
    "S03": _render_swiss_file_card,
    "S04": _render_swiss_interface_mock,
    "S05": _render_swiss_warning_rows,
    "S06": _render_swiss_pipeline,
    "S07": _render_swiss_takeaway_ledger,
    "S08": _render_swiss_image_hero,
    "S09": _render_swiss_kpi_tower,
    "S10": _render_swiss_hbar,
    "S11": _render_swiss_stacked_ledger,
    "S12": _render_swiss_matrix,
    "S13": _render_swiss_map_route,
}


EDITORIAL_RENDERERS = {
    "M01": _render_editorial_cover,
    "M02": _render_field_note_photo,
    "M03": _render_editorial_essay,
    "M04": _render_editorial_quote,
    "M05": _render_checklist,
    "M06": _render_evidence_wall,
    "M07": _render_ledger,
    "M08": _render_ledger,
    "M09": _render_atmospheric_thesis,
    "M10": _render_evidence_feature,
    "M11": _render_marginalia,
    "M12": _render_section_divider,
    "M13": _render_hero_question,
    "M14": _render_pipeline,
    "M15": _render_before_after,
    "M16": _render_image_led_cover,
}


def render_page_section(page: dict, mode: str = "editorial") -> str:
    recipe = page.get("recipe", "")
    if mode == "editorial":
        if not recipe.startswith("M"):
            raise ValueError(f"Recipe {recipe} does not match guizang mode {mode}")
        if recipe not in EDITORIAL_RENDERERS:
            raise ValueError(f"Unsupported editorial recipe: {recipe}")
        return EDITORIAL_RENDERERS[recipe](page)
    if mode == "swiss":
        if not recipe.startswith("S"):
            raise ValueError(f"Recipe {recipe} does not match guizang mode {mode}")
        if recipe not in SWISS_RENDERERS:
            raise ValueError(f"Unsupported swiss recipe: {recipe}")
        return SWISS_RENDERERS[recipe](page)
    raise ValueError(f"Unknown guizang mode: {mode}")
