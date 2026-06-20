"""
封面图生成器
使用 Gemini 3 Pro Image 生成播客/视频封面图

用法: python3 generate_cover.py <title> <output_path>
"""

import os
import json
import requests
import base64
import sys
import re
import random
import glob
import time
from config_loader import load_sources_config

STYLES_DIR = os.path.join(os.getcwd(), "styles")
# Ensure local styles dir exists and populate it if needed
if not os.path.exists(STYLES_DIR):
    os.makedirs(STYLES_DIR)
    # Copy global styles if they exist
    global_styles = "/Users/Avis/.agents/skills/baoyu-cover-image/references/styles"
    if os.path.exists(global_styles):
        import shutil
        for f in glob.glob(os.path.join(global_styles, "*.md")):
            shutil.copy(f, STYLES_DIR)

def load_config():
    return load_sources_config('config/sources.yaml')


def get_color_palette_for_topic(title):
    """
    根据标题内容判断主题领域，返回对应的配色方案。
    
    支持的领域：
    - 艺术/美学：暖色调，博物馆质感
    - 科技/未来：冷色调，霓虹感
    - 哲学/思想：深沉中性色，沉思感
    - 历史/文化：复古暖色，岁月感
    - 社会/政治：对比强烈，新闻感
    - 自然/环境：绿色系，生机感
    - 心理/情感：柔和渐变，温暖感
    - 文学/诗歌：水墨风，意境感
    - 经济/商业：稳重蓝色，专业感
    - 默认：多彩但和谐的配色
    """
    title_lower = title.lower()
    
    # 艺术/美学领域
    art_keywords = ['艺术', '美术', '绘画', '画家', '雕塑', '博物馆', '美学', '审美', 
                    '设计', '摄影', '建筑', '装置', '展览', 'art', 'museum', 'painting']
    if any(kw in title_lower for kw in art_keywords):
        return {
            'palette_description': 'Museum-quality sophistication with rich earth tones and gallery lighting',
            'primary_colors': 'Burnt sienna, terracotta, deep burgundy, warm ochre',
            'accent_colors': 'Antique gold, cream white, charcoal grey',
            'text_color': 'Aged ivory or warm cream that complements the earthy background',
            'mood': 'Contemplative, refined, culturally rich',
            'inspiration': 'Renaissance gallery walls, Vermeer lighting, classic art catalogs',
            'theme_hint': 'Evoke the warmth of a candlelit gallery or the texture of aged canvas.'
        }
    
    # 科技/未来领域
    tech_keywords = ['科技', '人工智能', 'AI', '技术', '数字', '互联网', '算法', '编程',
                     '机器人', '量子', '虚拟', '元宇宙', 'tech', 'digital', 'future']
    if any(kw in title_lower for kw in tech_keywords):
        return {
            'palette_description': 'Futuristic cyberpunk aesthetics with electric neon and deep shadows',
            'primary_colors': 'Electric blue, deep purple, midnight black',
            'accent_colors': 'Neon cyan, magenta pink, holographic silver',
            'text_color': 'Glowing cyan or electric blue with subtle neon glow effect',
            'mood': 'Cutting-edge, mysterious, forward-thinking',
            'inspiration': 'Blade Runner cityscape, Tron aesthetics, sci-fi book covers',
            'theme_hint': 'Create a sense of digital depth and technological wonder.'
        }
    
    # 哲学/思想领域
    philosophy_keywords = ['哲学', '思想', '存在', '意识', '认知', '伦理', '道德', '本质',
                          '真理', '理性', '自由意志', '形而上', 'philosophy', 'mind']
    if any(kw in title_lower for kw in philosophy_keywords):
        return {
            'palette_description': 'Deep contemplative tones evoking intellectual depth and mystery',
            'primary_colors': 'Slate grey, deep navy, muted indigo',
            'accent_colors': 'Soft silver, pale moonlight, dusty rose',
            'text_color': 'Soft silver or pale grey with ethereal quality',
            'mood': 'Meditative, profound, intellectually stimulating',
            'inspiration': 'Academic press covers, monastery libraries, Rothko paintings',
            'theme_hint': 'Suggest the weight of ideas and the depth of contemplation.'
        }
    
    # 历史/文化领域
    history_keywords = ['历史', '古代', '朝代', '帝国', '文明', '传统', '遗产', '考古',
                       '文物', '典籍', '古典', 'history', 'ancient', 'heritage']
    if any(kw in title_lower for kw in history_keywords):
        return {
            'palette_description': 'Vintage sepia tones with aged paper texture and classical elegance',
            'primary_colors': 'Sepia brown, antique gold, deep mahogany',
            'accent_colors': 'Faded ivory, dusty rose, aged bronze',
            'text_color': 'Antique gold or aged bronze with weathered patina',
            'mood': 'Nostalgic, dignified, timelessly elegant',
            'inspiration': 'Ancient manuscripts, vintage maps, classic history books',
            'theme_hint': 'Evoke the patina of time and the weight of centuries.'
        }
    
    # 社会/政治领域
    social_keywords = ['社会', '政治', '权力', '制度', '民主', '公民', '阶层', '不平等',
                      '革命', '运动', '抗争', 'social', 'political', 'power']
    if any(kw in title_lower for kw in social_keywords):
        return {
            'palette_description': 'Bold contrasts with editorial punch and newsroom gravitas',
            'primary_colors': 'Deep crimson, stark white, jet black',
            'accent_colors': 'Steel grey, newspaper yellow, urgent orange',
            'text_color': 'Bold white or stark black for maximum impact',
            'mood': 'Urgent, thought-provoking, socially conscious',
            'inspiration': 'Time Magazine covers, documentary posters, protest art',
            'theme_hint': 'Convey the tension and importance of social discourse.'
        }
    
    # 自然/环境领域
    nature_keywords = ['自然', '生态', '环境', '气候', '动物', '植物', '海洋', '森林',
                      '地球', '可持续', 'nature', 'ecology', 'environment']
    if any(kw in title_lower for kw in nature_keywords):
        return {
            'palette_description': 'Organic earth tones and lush natural greens with vitality',
            'primary_colors': 'Forest green, ocean teal, earthy brown',
            'accent_colors': 'Sunrise orange, wildflower purple, sky blue',
            'text_color': 'Cream white or pale sage that breathes with nature',
            'mood': 'Vibrant, life-affirming, environmentally conscious',
            'inspiration': 'National Geographic covers, nature documentaries, botanical illustrations',
            'theme_hint': 'Celebrate the beauty and fragility of the natural world.'
        }
    
    # 心理/情感领域
    psychology_keywords = ['心理', '情感', '情绪', '焦虑', '抑郁', '幸福', '关系', '亲密',
                          '创伤', '疗愈', '自我', 'psychology', 'emotion', 'mental']
    if any(kw in title_lower for kw in psychology_keywords):
        return {
            'palette_description': 'Soft gradients and warm tones evoking emotional depth',
            'primary_colors': 'Soft lavender, warm peach, gentle coral',
            'accent_colors': 'Misty blue, sunset pink, healing green',
            'text_color': 'Warm cream or soft white with gentle glow',
            'mood': 'Empathetic, introspective, healing',
            'inspiration': 'Therapy book covers, mindfulness apps, impressionist soft focus',
            'theme_hint': 'Create a safe space for emotional exploration.'
        }
    
    # 文学/诗歌领域
    literature_keywords = ['文学', '诗', '小说', '散文', '作家', '写作', '叙事', '故事',
                          '阅读', '书籍', 'literature', 'poetry', 'novel', 'writer']
    if any(kw in title_lower for kw in literature_keywords):
        return {
            'palette_description': 'Ink wash aesthetics with poetic brushstrokes and literary elegance',
            'primary_colors': 'Ink black, rice paper white, misty grey',
            'accent_colors': 'Cherry blossom pink, jade green, vermillion red',
            'text_color': 'Traditional ink black or cinnabar red with calligraphic grace',
            'mood': 'Poetic, evocative, literarily refined',
            'inspiration': 'Chinese ink painting, Penguin Classics, literary magazine covers',
            'theme_hint': 'Let words and images dance together in harmonious composition.'
        }
    
    # 经济/商业领域
    business_keywords = ['经济', '金融', '商业', '投资', '市场', '创业', '管理', '战略',
                        '货币', '资本', 'business', 'economy', 'finance', 'market']
    if any(kw in title_lower for kw in business_keywords):
        return {
            'palette_description': 'Professional sophistication with corporate elegance',
            'primary_colors': 'Navy blue, charcoal grey, deep teal',
            'accent_colors': 'Metallic gold, silver accents, pure white',
            'text_color': 'Crisp white or metallic gold for executive presence',
            'mood': 'Authoritative, trustworthy, professionally refined',
            'inspiration': 'Harvard Business Review, The Economist, financial reports',
            'theme_hint': 'Project confidence and analytical clarity.'
        }
    
    # 女性/性别领域
    gender_keywords = ['女性', '女权', '性别', '厌女', '母职', 'feminism', 'gender', 'women']
    if any(kw in title_lower for kw in gender_keywords):
        return {
            'palette_description': 'Empowering tones with artistic boldness and feminine strength',
            'primary_colors': 'Deep magenta, royal purple, passionate red',
            'accent_colors': 'Soft pink, ivory, midnight blue',
            'text_color': 'Bold white or soft cream with elegant femininity',
            'mood': 'Empowering, thought-provoking, artistically bold',
            'inspiration': 'Feminist art, contemporary gallery exhibitions, Frida Kahlo palette',
            'theme_hint': 'Celebrate feminine power and critical discourse.'
        }
    
    return {
        'palette_description': 'Rich, sophisticated palette with museum-quality depth and subtle gradients',
        'primary_colors': 'Deep teal, burnt umber, muted olive',
        'accent_colors': 'Antique gold, dusty rose, soft cream',
        'text_color': 'Colors that harmonize with the background - warm ivory, soft gold, or muted tones',
        'mood': 'Evocative, atmospheric, intellectually stimulating',
        'inspiration': 'New Yorker covers, Penguin Classics, art house film posters',
        'theme_hint': 'Create a unique visual identity that captures the essence of this topic.'
    }


def call_gemini_text(prompt):
    """
    调用 LLM 文本模型 (支持 Gemini 原生和 OpenAI 兼容格式)
    """
    config = load_config()
    api_config = config['api_keys']['llm']
    
    base_url = api_config['base_url']
    api_key = api_config['api_key']
    provider = api_config.get('provider', 'third_party')
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    if provider == 'openai_compatible':
        url = base_url
        payload = {
            "model": api_config['model'],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "top_p": 0.95,
            "max_tokens": 2048,
        }
    else:
        url = base_url
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json"
            }
        }
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120,
        )
        
        if response.status_code != 200:
            print(f"Error calling LLM Text API: {response.text}")
            return None
            
        result = response.json()
        
        if provider == 'openai_compatible':
            if 'choices' in result and result['choices']:
                return result['choices'][0].get('message', {}).get('content', '')
            return None
        else:
            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    final_text = ""
                    for part in candidate['content']['parts']:
                        if part.get('thought', False):
                            continue
                        if 'text' in part:
                            final_text += part['text']
                    return final_text
            return None
    except Exception as e:
        print(f"Exception calling LLM Text API: {e}")
        return None

def analyze_content_style(title, content):
    """
    使用 LLM 分析内容并选择最佳风格
    """
    # 获取可用风格列表
    if not os.path.exists(STYLES_DIR):
        return None, None
        
    style_files = glob.glob(os.path.join(STYLES_DIR, "*.md"))
    # 排除 blueprint.md 以及用户明确禁止的风格
    excluded_styles = ["blueprint", "watercolor", "flat-doodle", "pixel-art", "fantasy-animation", "playful"]
    styles = [os.path.basename(f).replace(".md", "") for f in style_files 
              if not any(ex in f for ex in excluded_styles)]
    
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
            # Try to find JSON object in the response
            json_str = response
            # Remove markdown code blocks if present
            if "```json" in json_str:
                match = re.search(r'```json\n(.*?)\n```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            elif "```" in json_str:
                match = re.search(r'```\n(.*?)\n```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            
            # Find first { and last }
            start = json_str.find('{')
            end = json_str.rfind('}')
            if start != -1 and end != -1:
                json_str = json_str[start:end+1]
                
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
        with open(style_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading style file: {e}")
        return None

def get_random_style():
    """(Deprecated) 从全局 Skills 目录随机加载一个样式定义"""
    # Keep for fallback
    if not os.path.exists(STYLES_DIR):
        return None, None
    style_files = glob.glob(os.path.join(STYLES_DIR, "*.md"))
    style_files = [f for f in style_files if "blueprint.md" not in f]
    if not style_files: return None, None
    selected_file = random.choice(style_files)
    style_name = os.path.basename(selected_file).replace(".md", "")
    with open(selected_file, 'r', encoding='utf-8') as f: content = f.read()
    return style_name, content

def parse_style_content(content):
    """解析样式文件内容"""
    if not content:
        return {}
        
    sections = {}
    current_section = "General"
    sections[current_section] = []
    
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('## '):
            current_section = line.replace('## ', '').strip()
            sections[current_section] = []
        else:
            sections[current_section].append(line)
            
    return sections


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
            # Try to find JSON object in the response
            json_str = response
            if "```json" in json_str:
                match = re.search(r'```json\n(.*?)\n```', json_str, re.DOTALL)
                if match: json_str = match.group(1)
            elif "```" in json_str:
                match = re.search(r'```\n(.*?)\n```', json_str, re.DOTALL)
                if match: json_str = match.group(1)
                
            start = json_str.find('{')
            end = json_str.rfind('}')
            if start != -1 and end != -1:
                json_str = json_str[start:end+1]
                
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
    
    # Retry configuration
    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"🎨 Generating cover image (Attempt {attempt + 1}/{max_retries})...")
            print(f"   Prompt preview: {prompt[:100]}...")
            
            response = requests.post(
                base_url,
                headers=headers,
                json=payload,
                timeout=120,
            )
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 429:
                wait_time = retry_delay * (2 ** attempt)
                print(f"   ⚠️ Rate limit hit (429). Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue

            if response.status_code != 200:
                print(f"   ❌ API error: {response.text[:300]}")
                # For server errors, try retrying
                if response.status_code in [500, 502, 503, 504]:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"   ⚠️ Server error ({response.status_code}). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
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
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"   Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            return False
            
        except (requests.exceptions.RequestException, Exception) as e:
            print(f"   ❌ Error generating image: {e}")
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                print(f"   Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return False


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
        # - (Hyphen, added)
        temp_title = clean_title
        for sep in ['：', '—', ' - ', '｜', '︱', '丨', '│', '|', '-']:
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
            # 优先使用最长的非数字结尾部分（通常是核心标题，避免选中短前缀如嘉宾名）
            if non_numeric_end_parts:
                non_numeric_end_parts.sort(key=len, reverse=True)
                clean_title = non_numeric_end_parts[0]
            else:
                # 如果都是数字结尾，也选最长的
                valid_parts.sort(key=len, reverse=True)
                clean_title = valid_parts[0]
                
            # 如果选中的部分看起来像 "午后偏见030"，尝试去掉数字
            if re.search(r'[\u4e00-\u9fa5]+\d+$', clean_title):
                 match = re.match(r'^(.*?)\d+$', clean_title)
                 if match:
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

    # 2. 获取内容上下文
    context = description or ""
    if content_path and os.path.exists(content_path):
        try:
            with open(content_path, 'r', encoding='utf-8') as f:
                # 读取前 2000 个字符作为上下文
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
        selected_type = "Conceptual" # Default fallback

    if not style_name or not style_content:
        print("Warning: No styles found, using hardcoded default.")
        style_name = "Default"
        style_data = {
            "Visual Elements": ["Clean composition", "High contrast"],
            "Color Palette": ["Deep Blue", "Gold", "White"],
            "Mood": ["Professional", "Engaging"]
        }
    else:
        style_data = parse_style_content(style_content)

    # 4. 确保类型存在
    if not selected_type:
        selected_type = "Conceptual"

    # 5. 构建 Prompt (仿照 Baoyu Skill Step 3)
    
    # 提取样式详情
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
