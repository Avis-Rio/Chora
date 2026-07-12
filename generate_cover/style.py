"""Visual-style selection and parsing for Chora covers.

Extracted from the legacy ``generate_cover.py`` on 2026-07-11 as part of the
L5 split tracked in ``skills/ARCHITECTURE.md`` §6. Hosts four small helpers
that participate in the ``generate_podcast_cover`` pipeline:

- :func:`analyze_content_style` — asks an LLM to pick the best visual style
  + cover type for a given content snippet.
- :func:`get_style_content` — loads the markdown style definition for a
  named style.
- :func:`get_random_style` — fallback that returns a random style.
- :func:`parse_style_content` — parses a style markdown file into a
  ``{section: [lines]}`` dict.
"""

import glob
import json
import os
import random
import re

from generate_cover._infra import STYLES_DIR, call_gemini_text

# Styles explicitly excluded from automatic selection (mostly cute/cartoon
# styles that don't fit the editorial aesthetic).
_EXCLUDED_STYLES = [
    "blueprint",
    "watercolor",
    "flat-doodle",
    "pixel-art",
    "fantasy-animation",
    "playful",
]


def analyze_content_style(title, content):
    """
    使用 LLM 分析内容并选择最佳风格
    """
    if not os.path.exists(STYLES_DIR):
        return None, None

    style_files = glob.glob(os.path.join(STYLES_DIR, "*.md"))
    styles = [
        os.path.basename(f).replace(".md", "")
        for f in style_files
        if not any(ex in f for ex in _EXCLUDED_STYLES)
    ]

    prompt = f"""
You are an expert art director. Analyze the following content and select the most appropriate visual style for a podcast cover.

**Content Title**: {title}
**Content Excerpt**:
{content[:1500]}

**Available Styles**:
{', '.join(styles)}

**Cover Types**:
- Metaphor (Concrete object representing abstract idea)
- Conceptual (Abstract shapes representing core concepts)
- Hero (Large focal visual, dramatic composition)
- Scene (Atmospheric environment, narrative elements)

**Task**:
1. Analyze the tone, theme, and subject matter of the content.
2. Select the ONE best style from the Available Styles list that fits this content.
   - **CRITICAL**: The user STRONGLY PREFERS the 'chora-style' (a custom blend of vintage, elegant, and Mingchao typography).
   - ALWAYS consider 'chora-style' as the top candidate for Philosophy, History, Culture, and Deep Thought content.
   - Only choose other styles if the content is strictly Tech/News/Business and 'chora-style' would be inappropriate.
   - AVOID: 'watercolor', 'flat-doodle', 'playful', 'pixel-art', 'fantasy-animation'.
3. Select the ONE best Cover Type.
   - **CRITICAL**: For abstract concepts (like "Language", "Being"), choose 'Metaphor' and think of a CONCRETE physical object (e.g., stone, ancient book, ruins, light beam) to represent it. Avoid abstract geometric shapes.
4. Provide a short reasoning (Keep it concise, under 50 words).

**Example Output**:
{{
  "selected_style": "dark-atmospheric",
  "selected_type": "Metaphor",
  "reasoning": "The content deals with heavy philosophical themes. Using a concrete metaphor like an ancient ruin with dramatic lighting fits the 'dark-atmospheric' style best."
}}

**Output Format**:
Return ONLY a valid JSON object. Do not include any markdown formatting, code blocks, or conversational text.
{{
  "selected_style": "style_name",
  "selected_type": "type_name",
  "reasoning": "explanation"
}}
"""

    print("🤔 Analyzing content for style selection...")
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
            return data.get("selected_style"), data.get("selected_type")
        except json.JSONDecodeError:
            print(f"Error parsing JSON response from LLM. Raw response:\n{response}")

    return None, None


def get_style_content(style_name):
    """读取特定样式的定义内容"""
    if not style_name:
        return None

    style_path = os.path.join(STYLES_DIR, f"{style_name}.md")
    if not os.path.exists(style_path):
        print(f"Style file not found: {style_path}")
        return None

    try:
        with open(style_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading style file: {e}")
        return None


def get_random_style():
    """(Deprecated) 从全局 Skills 目录随机加载一个样式定义"""
    if not os.path.exists(STYLES_DIR):
        return None, None
    style_files = glob.glob(os.path.join(STYLES_DIR, "*.md"))
    style_files = [f for f in style_files if "blueprint.md" not in f]
    if not style_files:
        return None, None
    selected_file = random.choice(style_files)
    style_name = os.path.basename(selected_file).replace(".md", "")
    with open(selected_file, "r", encoding="utf-8") as f:
        content = f.read()
    return style_name, content


def parse_style_content(content):
    """解析样式文件内容"""
    if not content:
        return {}

    sections = {}
    current_section = "General"
    sections[current_section] = []

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("## "):
            current_section = line.replace("## ", "").strip()
            sections[current_section] = []
        else:
            sections[current_section].append(line)

    return sections
