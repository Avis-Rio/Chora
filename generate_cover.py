"""
封面图生成器
使用 Gemini 3 Pro Image 生成播客/视频封面图

用法: python3 generate_cover.py <title> <output_path>
"""

import yaml
import json
import requests
import base64
import os
import sys
import re

def load_config():
    with open('config/sources.yaml', 'r') as f:
        return yaml.safe_load(f)


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
    
    # 移除 xiaoyuzhou_ 前缀
    if dir_name.startswith('xiaoyuzhou_'):
        dir_name = dir_name[len('xiaoyuzhou_'):]
    
    # 先处理 _-_ 分隔符（截断后缀）
    if '_-_' in dir_name:
        dir_name = dir_name.split('_-_')[0]
    
    # 按下划线分割
    parts = dir_name.split('_')
    
    if len(parts) < 2:
        return dir_name if dir_name else original
    
    # 跳过频道名（第一部分）
    remaining_parts = parts[1:]
    
    # 过滤掉常见前缀
    filtered = []
    for part in remaining_parts:
        # 跳过 FULL, EP, E 等前缀
        if part.upper() in ['FULL', 'EP', 'E']:
            continue
        filtered.append(part)
    
    if not filtered:
        # 如果全被过滤掉了，尝试用第一个有效部分
        return parts[1] if len(parts) > 1 else original
    
    # 取第一个有效部分作为标题候选（通常是最重要的）
    title_candidate = filtered[0]
    
    # 处理类似 "午后偏见030厌女、母职与消失的女性" 的情况
    # 尝试分离系列名+编号和实际标题
    # 模式：中文+数字+中文（系列名+编号+实际标题）
    series_match = re.match(r'^([^0-9]+)(\d+)(.+)$', title_candidate)
    if series_match:
        series_name = series_match.group(1)  # 午后偏见
        series_num = series_match.group(2)   # 030
        actual_title = series_match.group(3) # 厌女、母职与消失的女性
        # 如果实际标题部分足够长，使用它；否则保留完整
        if len(actual_title) >= 4:
            title_candidate = actual_title
    
    # 处理括号中的副标题
    # 如 "个人主义的复杂性（个人主义平民社会1）" -> "个人主义的复杂性"
    paren_match = re.match(r'^([^（]+)（.*）$', title_candidate)
    if paren_match:
        main_title = paren_match.group(1).strip()
        if len(main_title) >= 4:
            title_candidate = main_title
    
    # 英文括号也处理
    paren_match_en = re.match(r'^([^(]+)\(.*\)$', title_candidate)
    if paren_match_en:
        main_title = paren_match_en.group(1).strip()
        if len(main_title) >= 4:
            title_candidate = main_title
    
    return title_candidate.strip() if title_candidate.strip() else original

def generate_cover(prompt, output_path, title=None):
    """
    使用 Gemini 3 Pro Image 生成封面图
    
    Args:
        prompt: 生成提示词
        output_path: 输出文件路径
        title: 可选的标题，用于增强提示词
    
    Returns:
        bool: 是否成功生成
    """
    config = load_config()
    api_config = config['api_keys']['gemini']
    
    # 使用 Bearer Token 认证方式（云雾 API 要求）
    base_url = api_config['base_url']
    api_key = api_config['api_key']
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.9,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 8192
        }
    }
    
    print(f"🎨 Generating cover image...")
    print(f"   Prompt preview: {prompt[:100]}...")
    
    try:
        response = requests.post(
            base_url,
            headers=headers,
            json=payload,
            timeout=120,
        )
        
        print(f"   Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ API error: {response.text[:300]}")
            return False
        
        result = response.json()
        
        # 提取图像数据
        if 'candidates' in result and result['candidates']:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                parts = candidate['content']['parts']
                for part in parts:
                    inline_data = part.get('inlineData') or part.get('inline_data')
                    if inline_data:
                        image_data = base64.b64decode(inline_data['data'])
                        
                        dirname = os.path.dirname(output_path)
                        if dirname:
                            os.makedirs(dirname, exist_ok=True)
                        
                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                        
                        file_size_kb = len(image_data) / 1024
                        print(f"   ✅ Cover saved: {output_path} ({file_size_kb:.1f} KB)")
                        return True
                    elif 'text' in part:
                        print(f"   ⚠️ Model returned text instead of image")
                        print(f"   Text: {part['text'][:200]}...")
        
        print("   ❌ No image data found in response")
        return False
        
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error generating image: {e}")
        return False


def generate_podcast_cover(title, channel, output_path, description=None):
    """
    为播客生成封面图
    
    封面风格要求：
    - 艺术性主题插画，符合内容主旨
    - 包含醒目的中文标题文字
    - 无频道名/播客名/水印
    - 16:9 比例
    - 专业、有深度的视觉设计
    
    Args:
        title: 播客标题（将显示在封面上）
        channel: 频道名称（仅用于理解上下文，不显示）
        output_path: 输出路径
        description: 可选的内容描述，用于生成更精准的主题
    """
    
    # 清理标题，仅保留核心主题
    clean_title = title
    
    # 1. 移除明确的 "标题：" 前缀
    if clean_title.startswith("标题：") or clean_title.startswith("Title:"):
        clean_title = clean_title.split("：", 1)[-1].split(":", 1)[-1].strip()

    # 1.5 移除括号及其内容（包括中文和英文括号）
    clean_title = re.sub(r'（.*?）', '', clean_title)
    clean_title = re.sub(r'\(.*?\)', '', clean_title)
    clean_title = clean_title.strip()

    # 2. 尝试根据分隔符拆分
    parts = []
    # 统一分隔符 - 包括各种竖线和分隔符变体
    # ｜ (U+FF5C Fullwidth Vertical Line)
    # ︱ (U+FE31 Presentation Form for Vertical EM Dash)
    # | (U+007C Vertical Line)
    # ： (U+FF1A Fullwidth Colon)
    # — (U+2014 Em Dash)
    temp_title = clean_title
    for sep in ['：', '—', ' - ', '｜', '︱', '丨', '│', '|']:
        temp_title = temp_title.replace(sep, '|')
    if '|' in temp_title:
        parts = [p.strip() for p in temp_title.split('|')]
    else:
        parts = [clean_title]

    # 3. 过滤掉不想要的部分
    valid_parts = []
    for part in parts:
        # 忽略空字符串
        if not part:
            continue
            
        # 忽略纯数字或极短的数字组合
        if part.isdigit() or (len(part) < 5 and any(c.isdigit() for c in part)):
            continue
            
        # 忽略类似 "Vol.12", "EP01", "No.3" 的部分
        if re.match(r'^(Vol|Ep|No|Part)\.?\s*\d+', part, re.IGNORECASE):
            continue
        
        # 忽略类似 "午后偏见043" 这种 "中文+数字" 的系列名+期数格式
        # 匹配条件：纯中文开头 + 数字结尾，且总长度较短（通常系列名不会太长）
        if re.match(r'^[\u4e00-\u9fa5]+\d+$', part) and len(part) <= 10:
            continue
            
        # 忽略包含频道名的部分（如果提供了频道名）
        if channel and channel != "Unknown":
            # 简单的模糊匹配：如果部分包含频道名，或者频道名包含部分
            if channel in part or part in channel:
                continue
            # 处理类似 "午后偏见030" 这样的系列名+编号
            # 如果部分以数字结尾，且去掉数字后是频道名的一部分
            base_part = re.sub(r'\d+$', '', part).strip()
            if base_part and (base_part in channel or channel in base_part):
                continue

        valid_parts.append(part)

    # 4. 选择最佳部分：优先选择第一个有效部分（通常是核心标题）
    if valid_parts:
        # 过滤掉以数字结尾的部分
        non_numeric_end_parts = [p for p in valid_parts if not re.search(r'\d+$', p)]
        # 优先使用第一个不以数字结尾的部分
        if non_numeric_end_parts:
            clean_title = non_numeric_end_parts[0]
        else:
            clean_title = valid_parts[0]
            
        # 如果选中的部分看起来像 "午后偏见030"，尝试去掉数字
        if re.search(r'[\u4e00-\u9fa5]+\d+$', clean_title):
             match = re.match(r'^(.*?)\d+$', clean_title)
             if match:
                 # 只有当去掉数字后剩下的太短（可能是系列名），且我们没有其他选择时，才这样做
                 # 但通常如果只剩这个，可能就是标题。
                 # 用户特例：午后偏见030 -> 应该被过滤掉，保留后面的。
                 # 如果 valid_parts 里有 "午后偏见030" 和 "厌女..."，上面的逻辑应该已经选了 "厌女..."（因为更长且没数字结尾）
                 pass
    else:
        # 如果过滤完没了，回退到原始标题
        clean_title = title
        # 再次清理括号，以防万一回退到了带括号的标题
        clean_title = re.sub(r'（.*?）', '', clean_title)
        clean_title = re.sub(r'\(.*?\)', '', clean_title)
        clean_title = clean_title.strip()

    # 移除常见前缀字符
    for prefix in ['FULL ', 'EP', 'E', '#', '【', '】']:
        if clean_title.startswith(prefix):
            clean_title = clean_title[len(prefix):].strip()
            
    # 长度截断
    if len(clean_title) > 30:
        clean_title = clean_title[:28] + "..."
    
    # 构建提示词
    prompt = f"""Create a visually stunning podcast cover image with the following specifications:

**CRITICAL REQUIREMENTS:**
1. **MUST include Chinese title text**: "{clean_title}" - elegantly placed within the composition
2. **16:9 aspect ratio** - horizontal layout suitable for podcast/video platforms
3. **NO series names, episode numbers, channel names, or watermarks** - ONLY display "{clean_title}"
4. **NO text like "午后偏见", "EP", numbers, or any attribution** - absolutely forbidden

**TYPOGRAPHY STYLE - EXTREMELY IMPORTANT:**
- **Font Style**: Traditional Chinese Mingchao/Songti (宋體) with vintage woodblock print texture
- **Font Size**: MODERATE SIZE - NOT too large, the title should occupy at most 30-40% of the image width
- **Placement**: Elegantly positioned, may be placed in a corner, along an edge, or integrated into the art
- **Visual Treatment**: Slightly distressed (微損), subtle ink bleed (墨暈感), aged letterpress feel
- **Stroke Style**: High contrast strokes (橫細豎粗), sharp serifs, scholarly elegance (儒雅書卷氣)
- **Color**: Use colors that harmonize with the background - can be warm gold, aged ivory, or muted tones

**ART STYLE - PRIORITIZE VISUAL ARTISTRY:**
- **Mood**: Evocative, atmospheric, intellectually stimulating
- **Style**: Oil painting texture, cinematic lighting, fine art illustration quality
- **Composition**: The ARTWORK should be the hero, with text as an elegant accent
- **Color Palette**: Rich, sophisticated, museum-quality - deep shadows, golden highlights, subtle gradients
- **Elements**: Abstract or symbolic imagery that captures the essence of "{title}"
- **Quality**: Premium book cover or high-end magazine editorial aesthetic
- **Inspiration**: Think New Yorker covers, Penguin Classics, art house film posters

**LAYOUT & BALANCE:**
- The visual artwork should dominate 60-70% of the composition
- Title text should feel like a natural part of the design, not stamped on top
- Ensure harmony between typography and illustrations
- Leave breathing room - avoid cluttered or cramped compositions

**Theme Interpretation:**
For the topic "{title}", create an evocative visual that captures its intellectual essence and emotional resonance."""

    if description:
        prompt += f"\n\n**Additional Context:**\nThe content discusses: {description[:300]}"
    
    return generate_cover(prompt, output_path, clean_title)


def regenerate_missing_covers():
    """
    扫描 content_archive 目录，为所有缺少封面的小宇宙播客生成封面
    """
    import glob
    
    archive_dir = "content_archive"
    xiaoyuzhou_dirs = glob.glob(f"{archive_dir}/**/xiaoyuzhou_*", recursive=True)
    
    regenerated = []
    failed = []
    
    for dir_path in xiaoyuzhou_dirs:
        if not os.path.isdir(dir_path):
            continue
            
        # 检查是否已有封面
        has_cover = any([
            os.path.exists(os.path.join(dir_path, "cover.png")),
            os.path.exists(os.path.join(dir_path, "cover.jpg")),
            os.path.exists(os.path.join(dir_path, "cover.jpeg"))
        ])
        
        if has_cover:
            print(f"⏭️ Skip (has cover): {dir_path}")
            continue
        
        # 优先从目录名提取原始标题（metadata.md 中的标题是 AI 重写后的版本）
        dir_name = os.path.basename(dir_path)
        title = extract_title_from_dirname(dir_name)
        
        # 读取 metadata 获取频道名等信息
        metadata_path = os.path.join(dir_path, "metadata.md")
        content = ""
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        # 提取频道名
        channel = "Unknown"
        if "小宇宙 - " in content:
            channel = content.split("小宇宙 - ")[1].split('\n')[0].strip()
        
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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 generate_cover.py <title> <output_path>")
        print("  python3 generate_cover.py --regenerate-all")
        sys.exit(1)
    
    if sys.argv[1] == "--regenerate-all":
        regenerate_missing_covers()
    else:
        if len(sys.argv) < 3:
            print("Error: Missing output_path argument")
            sys.exit(1)
        title = sys.argv[1]
        output_path = sys.argv[2]
        success = generate_podcast_cover(title, "Unknown", output_path)
        sys.exit(0 if success else 1)
