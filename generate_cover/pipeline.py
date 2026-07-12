"""Podcast cover generation pipeline for Chora.

Extracted from the monolithic ``generate_cover.py`` on 2026-07-11 as part of
the L5 split tracked in ``skills/ARCHITECTURE.md`` §6.

Public API (re-exported through ``generate_cover.__init__`` for
backwards compatibility):

- :func:`generate_podcast_cover` — Gemini-backed 16:9 cover for one episode.
  Title is LLM-cleaned, style auto-selected from local style catalogue, then a
  Baoyu-Skill-style prompt is sent to Gemini image.
- :func:`generate_podcast_cover_with_fallback` — Gemini first; on failure,
  delegates to Pexels / Unsplash via ``stock_cover_service``.
- :func:`regenerate_missing_covers` — CLI helper that scans ``content_archive``
  for podcast folders missing ``cover.{png,jpg,jpeg}`` and regenerates them.
  Restored from orphan code (the original function definition had been
  silently dropped while the docstring/body remained in place); the CLI at
  the bottom of ``generate_cover.py`` calls this.

All three depend on a small set of helpers that remain in
``generate_cover.py`` (intentionally kept co-located): ``clean_title_with_llm``,
``analyze_content_style``, ``get_style_content``, ``get_random_style``,
``parse_style_content``, ``extract_title_from_dirname``, ``generate_cover``.
"""

import os
import re

from generate_cover.image import generate_cover
from generate_cover.style import (
    analyze_content_style,
    get_random_style,
    get_style_content,
    parse_style_content,
)
from generate_cover.title import clean_title_with_llm, extract_title_from_dirname


def generate_podcast_cover(title, channel, output_path, description=None, content_path=None):
    """
    为播客生成封面图 (集成 Baoyu Skill 逻辑)

    Args:
        title: 播客标题
        channel: 频道名称
        output_path: 输出路径
        description: 可选的内容描述
        content_path: 可选的内容文件路径 (rewritten.md)
    """

    # 1. 尝试使用 LLM 清理标题 (优先)
    llm_clean_title = clean_title_with_llm(title)
    if llm_clean_title:
        clean_title = llm_clean_title
    else:
        # Fallback to manual cleaning if LLM fails
        print("⚠️ LLM title cleaning failed, falling back to manual logic.")
        clean_title = title

        # 1. 移除明确的 "标题：" 前缀
        if clean_title.startswith("标题：") or clean_title.startswith("Title:"):
            clean_title = clean_title.split("：", 1)[-1].split(":", 1)[-1].strip()

        # 1.5 移除括号及其内容（包括中文和英文括号）
        clean_title = re.sub(r"（.*?）", "", clean_title)
        clean_title = re.sub(r"\(.*?\)", "", clean_title)
        clean_title = clean_title.strip()

        # 2. 尝试根据分隔符拆分
        parts = []
        temp_title = clean_title
        for sep in ["：", "—", " - ", "｜", "︱", "丨", "│", "|", "-"]:
            temp_title = temp_title.replace(sep, "|")
        if "|" in temp_title:
            parts = [p.strip() for p in temp_title.split("|")]
        else:
            parts = [clean_title]

        # 3. 过滤掉不想要的部分
        valid_parts = []
        for part in parts:
            if not part:
                continue

            # 忽略纯数字或极短的数字组合
            if part.isdigit() or (len(part) < 5 and any(c.isdigit() for c in part)):
                continue

            # 忽略类似 "Vol.12", "EP01", "No.3" 的部分
            if re.match(r"^(Vol|Ep|No|Part)\.?\s*\d+", part, re.IGNORECASE):
                continue

            # 忽略类似 "午后偏见043" 这种 "中文+数字" 的系列名+期数格式
            if re.match(r"^[一-龥]+\d+$", part) and len(part) <= 10:
                continue

            # 忽略包含频道名的部分（如果提供了频道名）
            if channel and channel != "Unknown":
                if channel in part or part in channel:
                    continue
                base_part = re.sub(r"\d+$", "", part).strip()
                if base_part and (base_part in channel or channel in base_part):
                    continue

            valid_parts.append(part)

        # 4. 选择最佳部分
        if valid_parts:
            non_numeric_end_parts = [p for p in valid_parts if not re.search(r"\d+$", p)]
            if non_numeric_end_parts:
                non_numeric_end_parts.sort(key=len, reverse=True)
                clean_title = non_numeric_end_parts[0]
            else:
                valid_parts.sort(key=len, reverse=True)
                clean_title = valid_parts[0]

            if re.search(r"[一-龥]+\d+$", clean_title):
                match = re.match(r"^(.*?)\d+$", clean_title)
                if match:
                    pass
        else:
            clean_title = title
            clean_title = re.sub(r"（.*?）", "", clean_title)
            clean_title = re.sub(r"\(.*?\)", "", clean_title)
            clean_title = clean_title.strip()

        # 移除常见前缀字符
        for prefix in ["FULL ", "EP", "E", "#", "【", "】"]:
            if clean_title.startswith(prefix):
                clean_title = clean_title[len(prefix) :].strip()

        # 长度截断
        if len(clean_title) > 30:
            clean_title = clean_title[:28] + "..."

    # 2. 获取内容上下文
    context = description or ""
    if content_path and os.path.exists(content_path):
        try:
            with open(content_path, "r", encoding="utf-8") as f:
                file_content = f.read(2000)
                context += "\n" + file_content
        except Exception as e:
            print(f"Warning: Could not read content file: {e}")

    # 3. 智能选择风格 (LLM Analysis)
    style_name = None
    selected_type = None

    if context:
        style_name, selected_type = analyze_content_style(clean_title, context)

    if style_name:
        print(f"🎨 AI Selected Style: {style_name}")
        print(f"🎨 AI Selected Type: {selected_type}")
        style_content = get_style_content(style_name)
    else:
        print("⚠️ Style analysis failed or no context, falling back to random.")
        style_name, style_content = get_random_style()
        selected_type = "Conceptual"

    if not style_name or not style_content:
        print("Warning: No styles found, using hardcoded default.")
        style_name = "Default"
        style_data = {
            "Visual Elements": ["Clean composition", "High contrast"],
            "Color Palette": ["Deep Blue", "Gold", "White"],
            "Mood": ["Professional", "Engaging"],
        }
    else:
        style_data = parse_style_content(style_content)

    if not selected_type:
        selected_type = "Conceptual"

    # 4. 构建 Prompt
    visual_elements = ", ".join(style_data.get("Visual Elements", []))
    color_palette = ", ".join(style_data.get("Color Palette", []))
    mood = ", ".join(style_data.get("Mood", []) or style_data.get("Best For", []))

    prompt = f"""
Create a cinematic 16:9 cover image for a podcast episode.

**Cover Configuration:**
- **Theme**: {clean_title}
- **Type**: {selected_type}
- **Style**: {style_name}
- **Aspect Ratio**: 16:9
- **Language**: Chinese (for any text, though preferably no text or only title)

**Visual Composition:**
- **Main Visual**: Create a {selected_type.split(' ')[0]} visual that represents the core theme: "{clean_title}".
- **Style Characteristics**: {visual_elements}
- **Color Scheme**: {color_palette}
- **Mood/Atmosphere**: {mood}

**Special Instructions for Abstract Themes:**
If the theme is abstract (e.g., Philosophy, Language, Being), do NOT use abstract shapes. Instead, use **CONCRETE, TANGIBLE OBJECTS** with **HEAVY TEXTURES**.
- Examples: A weathered stone tablet, an ancient leather-bound book, a lonely lighthouse in a storm, a cracked marble statue, a deep forest path.
- Lighting: Cinematic, dramatic, volumetric lighting (God rays), chiaroscuro.
- Texture: Dust, scratches, grain, stone texture, paper texture.

**TYPOGRAPHY & TEXT STYLE (CRITICAL):**
- **Font**: MUST use **Traditional Chinese Mingchao/Songti (宋體)** style.
- **Aesthetic**: Elegant, scholarly, vintage woodblock print feel (resembling 汇文明朝体).
- **Treatment**: Subtle texture, integrated with the artwork, NOT generic digital text.
- **Layout**: Can be vertical or horizontal, mimicking high-end magazine or book covers.
- **Content**: ONLY display the title "{clean_title}". NO other text.

**Critical Requirements:**
1. **Aspect Ratio**: MUST be 16:9.
2. **Text**: The title "{clean_title}" must be legible but artistic.
3. **Quality**: 8k resolution, photorealistic or high-end artistic render.
3. **Quality**: 8k resolution, photorealistic or high-end artistic render (depending on style), detailed, aesthetic.

**Context for Visual Metaphor:**
{context[:500]}
"""

    return generate_cover(prompt, output_path, clean_title)


def generate_podcast_cover_with_fallback(
    title,
    channel,
    output_path,
    description=None,
    content_path=None,
):
    """
    为播客生成封面图：优先使用 Gemini 生成，失败时 fallback 到 Pexels/Unsplash。

    Args:
        title: 播客标题
        channel: 频道名称
        output_path: 输出路径
        description: 可选的内容描述
        content_path: 可选的内容文件路径 (rewritten.md)

    Returns:
        bool: 是否成功生成/下载封面
    """
    print(f"\n🖼️  Generating cover for: {title}")

    success = generate_podcast_cover(
        title=title,
        channel=channel,
        output_path=output_path,
        description=description,
        content_path=content_path,
    )
    if success:
        return True

    print("\n🔄 Gemini cover generation failed. Trying stock photo fallback...")

    fallback_description = description or ""
    if content_path and os.path.exists(content_path):
        try:
            with open(content_path, "r", encoding="utf-8") as f:
                content_text = f.read()
            fallback_description = f"{fallback_description} {content_text[:800]}".strip()
        except Exception:
            pass

    from stock_cover_service import download_stock_cover

    return download_stock_cover(
        title=title,
        output_path=output_path,
        description=fallback_description,
        providers=("pexels", "unsplash"),
        resize=True,
    )


def regenerate_missing_covers():
    """扫描 content_archive 目录，为所有缺少封面的小宇宙播客生成封面。

    Restored 2026-07-11 from orphan code: the function definition had been
    silently dropped while the docstring/body remained, causing any caller of
    ``python3 generate_cover.py --regenerate-all`` to crash with NameError.
    Kept in this module as it is the CLI counterpart of
    :func:`generate_podcast_cover` and shares the same Gemini config path.
    """
    import glob

    archive_dir = "content_archive"
    xiaoyuzhou_dirs = glob.glob(f"{archive_dir}/**/xiaoyuzhou_*", recursive=True)

    regenerated = []
    failed = []

    for dir_path in xiaoyuzhou_dirs:
        if not os.path.isdir(dir_path):
            continue

        has_cover = any(
            [
                os.path.exists(os.path.join(dir_path, "cover.png")),
                os.path.exists(os.path.join(dir_path, "cover.jpg")),
                os.path.exists(os.path.join(dir_path, "cover.jpeg")),
            ]
        )

        if has_cover:
            print(f"⏭️ Skip (has cover): {dir_path}")
            continue

        dir_name = os.path.basename(dir_path)
        title = extract_title_from_dirname(dir_name)

        metadata_path = os.path.join(dir_path, "metadata.md")
        content = ""
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                content = f.read()

        channel = "Unknown"
        if "小宇宙 - " in content:
            channel = content.split("小宇宙 - ")[1].split("\n")[0].strip()

        print(f"\n📍 Processing: {dir_path}")
        print(f"   Title: {title}")

        cover_path = os.path.join(dir_path, "cover.png")
        success = generate_podcast_cover(title, channel, cover_path)

        if success:
            regenerated.append(dir_path)
        else:
            failed.append(dir_path)

    print(f"\n{'='*50}")
    print(f"✅ Regenerated: {len(regenerated)}")
    print(f"❌ Failed: {len(failed)}")

    return regenerated, failed


__all__ = [
    "generate_podcast_cover",
    "generate_podcast_cover_with_fallback",
    "regenerate_missing_covers",
]
