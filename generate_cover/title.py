"""Title cleaning utilities for Chora covers.

Extracted from the legacy ``generate_cover.py`` on 2026-07-11 as part of the
L5 split tracked in ``skills/ARCHITECTURE.md`` §6. Hosts two helpers used by
the podcast cover pipeline:

- :func:`clean_title_with_llm` — LLM-driven title extraction (strips episode
  numbers, series prefixes, sponsor suffixes, etc.).
- :func:`extract_title_from_dirname` — regex/dirname heuristic that recovers
  the original (pre-AI) title when only a filesystem directory is available.
  Used by :func:`regenerate_missing_covers`.
"""

import json
import re

from generate_cover._infra import call_gemini_text


def clean_title_with_llm(title):
    """
    使用 LLM 智能提取核心标题
    """
    prompt = f"""
You are a professional editor. Extract the **Main Core Title** from the following podcast episode title.

**Input Title**: "{title}"

**Rules**:
1. Remove episode numbers (e.g., Vol.12, EP03, No.5).
2. Remove series names if they are separate from the main topic (e.g., "午后偏见", "翻转电台").
3. Remove dates, promotional suffixes, or channel names.
4. Remove part indicators like (上), (中), (下), (Part 1).
5. Remove academic or category tags like "20世纪重要思想".
6. Keep ONLY the specific topic of this episode.

**Examples**:
- Input: "Vol.123 忽左忽右 | 为什么我们都爱听播客" -> Output: "为什么我们都爱听播客"
- Input: "人，诗意栖居-晚期海德格尔（中）-20世纪重要思想-vol.27" -> Output: "人，诗意栖居"
- Input: "EP05 维生素E - 艺术作品的本源" -> Output: "艺术作品的本源"

**Output Format**:
Return ONLY a valid JSON object:
{{
  "clean_title": "The Cleaned Title"
}}
"""
    print(f"🧹 Cleaning title with AI: {title}")
    response = call_gemini_text(prompt)

    if response:
        try:
            json_str = response
            if "```json" in json_str:
                match = re.search(r"```json\n(.*?)\n```", json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            elif "```" in json_str:
                match = re.search(r"```\n(.*?)\n```", json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)

            start = json_str.find("{")
            end = json_str.rfind("}")
            if start != -1 and end != -1:
                json_str = json_str[start : end + 1]

            data = json.loads(json_str)
            cleaned = data.get("clean_title")
            if cleaned:
                print(f"   ✨ Cleaned Title: {cleaned}")
                return cleaned
        except Exception as e:
            print(f"Error parsing cleaned title: {e}")

    return None


def extract_title_from_dirname(dir_name):
    """
    从目录名提取原始标题

    目录名格式通常为：
    - xiaoyuzhou_频道名_标题...
    - xiaoyuzhou_频道名_FULL_标题...
    - xiaoyuzhou_频道名（别名）_FULL_标题（副标题）_-_后缀

    例如：
    - xiaoyuzhou_翻转台电（翻电）_FULL_个人主义的复杂性（个人主义平民社会1）_-_翻转电台知识分享
      -> 个人主义的复杂性
    - xiaoyuzhou_忽左忽右_午后偏见030厌女、母职与消失的女性
      -> 厌女、母职与消失的女性
    """
    original = dir_name

    if dir_name.startswith("xiaoyuzhou_"):
        dir_name = dir_name[len("xiaoyuzhou_") :]

    if "_-_" in dir_name:
        dir_name = dir_name.split("_-_")[0]

    parts = dir_name.split("_")

    if len(parts) < 2:
        return dir_name if dir_name else original

    remaining_parts = parts[1:]

    filtered = []
    for part in remaining_parts:
        if part.upper() in ["FULL", "EP", "E"]:
            continue
        filtered.append(part)

    if not filtered:
        return parts[1] if len(parts) > 1 else original

    title_candidate = filtered[0]

    series_match = re.match(r"^([^0-9]+)(\d+)(.+)$", title_candidate)
    if series_match:
        actual_title = series_match.group(3)
        if len(actual_title) >= 4:
            title_candidate = actual_title

    paren_match = re.match(r"^([^（]+)（.*）$", title_candidate)
    if paren_match:
        main_title = paren_match.group(1).strip()
        if len(main_title) >= 4:
            title_candidate = main_title

    paren_match_en = re.match(r"^([^(]+)\(.*\)$", title_candidate)
    if paren_match_en:
        main_title = paren_match_en.group(1).strip()
        if len(main_title) >= 4:
            title_candidate = main_title

    return title_candidate.strip() if title_candidate.strip() else original
