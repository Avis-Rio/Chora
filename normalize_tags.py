#!/usr/bin/env python3
"""
Tag Standardization Script
Normalizes tags in rewritten.md files to use standardized English taxonomy.
"""

import glob
import os
import re

# Standardized tag taxonomy (English)
VALID_TAGS = {
    # Academic Disciplines
    "Philosophy",
    "Sociology",
    "Psychology",
    "Anthropology",
    "History",
    "Political Science",
    "Economics",
    "Technology",
    "Medicine",
    "Law",
    # Research Fields
    "Gender Studies",
    "Cultural Studies",
    "Media Studies",
    "Religious Studies",
    "Neuroscience",
    "STS",
    # Conceptual Themes
    "Power & Politics",
    "Identity",
    "Ethics",
    "Capitalism",
    "Modernity",
    "Relationships",
    "Art & Aesthetics",
    # Format
    "Interview",
    "Deep Dive",
}

# Chinese to English mapping (including synonyms and related terms)
TAG_MAPPING = {
    # Academic Disciplines
    "哲学": "Philosophy",
    "社会学": "Sociology",
    "心理学": "Psychology",
    "人类学": "Anthropology",
    "历史": "History",
    "历史学": "History",
    "医疗史": "History",
    "政治": "Political Science",
    "政治学": "Political Science",
    "经济": "Economics",
    "经济学": "Economics",
    "科技": "Technology",
    "技术": "Technology",
    "医学": "Medicine",
    "医疗": "Medicine",
    "公共卫生": "Medicine",
    "法律": "Law",
    "法学": "Law",
    # Research Fields
    "性别": "Gender Studies",
    "性别研究": "Gender Studies",
    "女性": "Gender Studies",
    "女性主义": "Gender Studies",
    "厌女": "Gender Studies",
    "母职": "Gender Studies",
    "文化": "Cultural Studies",
    "文化研究": "Cultural Studies",
    "物质文化": "Cultural Studies",
    "媒体": "Media Studies",
    "传播": "Media Studies",
    "新闻": "Media Studies",
    "宗教": "Religious Studies",
    "神学": "Religious Studies",
    "神经科学": "Neuroscience",
    "脑科学": "Neuroscience",
    # Conceptual Themes
    "权力": "Power & Politics",
    "身体政治": "Power & Politics",
    "政治经济学": "Power & Politics",
    "身份": "Identity",
    "身份认同": "Identity",
    "伦理": "Ethics",
    "道德": "Ethics",
    "资本主义": "Capitalism",
    "资本": "Capitalism",
    "新自由主义": "Capitalism",
    "现代性": "Modernity",
    "后现代": "Modernity",
    "社会变迁": "Modernity",
    "爱情": "Relationships",
    "婚姻": "Relationships",
    "家庭": "Relationships",
    "亲密关系": "Relationships",
    "艺术": "Art & Aesthetics",
    "美学": "Art & Aesthetics",
    "文学": "Art & Aesthetics",
    "文学批评": "Art & Aesthetics",
    # Format
    "访谈": "Interview",
    "对话": "Interview",
    "深度": "Deep Dive",
    "纪录": "Deep Dive",
    "讲座": "Deep Dive",
    # Special mappings for specific content
    "炼丹术": "History",  # Historical practice
    "犯罪": "Sociology",
    "药物": "Medicine",
    "创作者经济": "Economics",
    # Additional mappings
    "AI": "Technology",
    "人工智能": "Technology",
    "脑机接口": "Neuroscience",
    "赛博格": "Technology",
    "博物馆": "Anthropology",
    "去殖民化": "Anthropology",
    "未来学": "Technology",
    "镜像世界": "Technology",
    "教育": "Sociology",
    "组织管理": "Sociology",
    "创新困境": "Economics",
    "权力结构": "Power & Politics",
}

# Blacklist - tags to remove entirely
BLACKLIST = {
    "忽左忽右",
    "硅谷101",
    "翻转电台",
    "翻转台电",
    "Dan Koe",
    "Kevin Kelly",
    "Unknown",
    "JustPod",
    "午后偏见",
    "翻电",
    "Gavin Wang",
    "Alex Wang",
    "中国",
    "美国",
    "欧洲",
    "日本",
    "中东",
    "拉美",
    "非洲",
    "China",
    "USA",
    "America",
    "Europe",
    "Japan",
}


def normalize_tag(tag):
    """Normalize a single tag to standard English form."""
    tag = tag.strip()

    # Check blacklist
    for bad in BLACKLIST:
        if bad.lower() in tag.lower():
            return None

    # If already in valid tags, return as-is
    if tag in VALID_TAGS:
        return tag

    # Try mapping
    if tag in TAG_MAPPING:
        return TAG_MAPPING[tag]

    # Check if it's a valid English tag with different casing
    for valid in VALID_TAGS:
        if tag.lower() == valid.lower():
            return valid

    # Unknown tag - skip it
    print(f"    ⚠️ Unknown tag skipped: {tag}")
    return None


def normalize_tags_in_file(file_path):
    """Normalize tags in a rewritten.md file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find tags line - support both Chinese and English formats
    # Pattern: 标签: or Tags:
    tag_match = re.search(r"(标签|Tags)[:：]\s*(.+)", content, re.IGNORECASE)

    if not tag_match:
        return False

    tag_match.group(1)
    tags_str = tag_match.group(2)

    # Split tags
    raw_tags = [t.strip() for t in re.split(r"[,，、]", tags_str) if t.strip()]

    # Normalize each tag
    normalized = set()
    for tag in raw_tags:
        norm = normalize_tag(tag)
        if norm:
            normalized.add(norm)

    # Sort for consistency
    final_tags = sorted(list(normalized))

    # Use English format
    new_line = f"Tags: {', '.join(final_tags)}"

    # Replace in content
    new_content = content.replace(tag_match.group(0), new_line)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        folder_name = os.path.basename(os.path.dirname(file_path))
        print(f"✅ {folder_name[:50]}...")
        print(f"   Old: {tags_str}")
        print(f"   New: {', '.join(final_tags)}")
        return True

    return False


def main():
    archive_dir = "content_archive"
    print(f"🔄 Normalizing tags in {archive_dir}...\n")

    count = 0
    for rewritten_path in glob.glob(f"{archive_dir}/*/*/rewritten.md"):
        if normalize_tags_in_file(rewritten_path):
            count += 1

    print(f"\n🎉 Normalization complete! Updated {count} files.")
    print(f"\n📋 Valid tags: {', '.join(sorted(VALID_TAGS))}")


if __name__ == "__main__":
    main()
