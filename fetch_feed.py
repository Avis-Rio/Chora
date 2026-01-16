import yaml
import os
import json
import subprocess
import re
from datetime import datetime, timedelta
from youtube_service import get_youtube_transcript

# 全局路径配置
CONFIG_PATH = 'config/sources.yaml'
STATE_PATH = 'config/state.yaml'

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"错误: 找不到配置文件 {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_state():
    if not os.path.exists(STATE_PATH):
        return {'processed_ids': []}
    with open(STATE_PATH, 'r', encoding='utf-8') as f:
        state = yaml.safe_load(f)
        if not state or 'processed_ids' not in state:
            return {'processed_ids': []}
        return state

def save_state(state):
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        yaml.safe_dump(state, f)

def get_safe_title(title):
    return re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")

def is_already_processed(state, content_id):
    return content_id in state.get('processed_ids', [])

def is_folder_exists(output_dir, date, platform, channel, title):
    safe_title = get_safe_title(title)
    # 新路径结构: {date}/{platform}_{channel}_{safe_title}
    date_dir = os.path.join(output_dir, date)
    if not os.path.exists(date_dir):
        return False
    
    folder_prefix = f"{platform}_{channel}_"
    for existing_folder in os.listdir(date_dir):
        if existing_folder.startswith(folder_prefix) and safe_title in existing_folder:
            return True
    return False

def fetch_youtube_feed(channel_id, name, min_duration, days, include_keywords, state):
    print(f"正在扫描 YouTube: {name}")
    # 使用日期（不含时间）来比较，确保包含边界日期
    cutoff_date = (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    items = []
    
    # 方法 1: 尝试 RSS Feed
    rss_items = _fetch_via_rss(channel_id, name, cutoff_date, min_duration, include_keywords, state)
    if rss_items:
        return rss_items
    
    # 方法 2: 使用 yt-dlp (带重试)
    print(f"  📡 RSS 失败，使用 yt-dlp...")
    ytdlp_items = _fetch_via_ytdlp(channel_id, name, cutoff_date, min_duration, include_keywords, state)
    return ytdlp_items

def _fetch_via_rss(channel_id, name, cutoff_date, min_duration, include_keywords, state):
    """通过 RSS Feed 获取视频列表"""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    items = []
    xml_content = ""
    
    # 重试 3 次
    for attempt in range(3):
        try:
            result = subprocess.run(
                ['curl', '-s', '-L', '--max-time', '20', rss_url], 
                capture_output=True, text=True, timeout=25
            )
            xml_content = result.stdout
            
            if xml_content and '<feed' in xml_content:
                break
            else:
                import time
                time.sleep(2)
        except Exception as e:
            import time
            time.sleep(2)
    
    if not xml_content or '<feed' not in xml_content:
        return []
    
    try:
        entries = re.findall(r'<entry>(.*?)</entry>', xml_content, re.DOTALL)
        
        for entry in entries:
            vid_match = re.search(r'<yt:videoId>([^<]+)</yt:videoId>', entry)
            if not vid_match:
                continue
            v_id = vid_match.group(1)
            
            if is_already_processed(state, v_id):
                continue
            
            title_match = re.search(r'<title>([^<]+)</title>', entry)
            title = title_match.group(1) if title_match else ''
            
            pub_match = re.search(r'<published>([^<]+)</published>', entry)
            if pub_match:
                pub_str = pub_match.group(1)[:10]
                try:
                    video_date = datetime.strptime(pub_str, '%Y-%m-%d')
                    if video_date < cutoff_date:
                        continue
                    formatted_date = pub_str
                except ValueError:
                    continue
            else:
                continue
            
            if include_keywords:
                if not any(kw.lower() in title.lower() for kw in include_keywords):
                    continue
            
            # 获取视频时长
            duration = _get_video_duration(v_id)
            if duration < min_duration:
                print(f"  ⏭️ 跳过 (时长不足): {title[:30]}... ({round(duration, 1)} 分钟)")
                continue
            
            items.append({
                'platform': 'youtube',
                'channel': name,
                'title': title,
                'date': formatted_date,
                'url': f"https://www.youtube.com/watch?v={v_id}",
                'id': v_id,
                'duration': round(duration, 1)
            })
    except Exception as e:
        print(f"  ⚠️ RSS 解析失败: {e}")
    
    return items

def _fetch_via_ytdlp(channel_id, name, cutoff_date, min_duration, include_keywords, state):
    """通过 yt-dlp 获取视频列表"""
    urls_to_try = [
        f'https://www.youtube.com/channel/{channel_id}/videos',
        f'https://www.youtube.com/@{name.replace(" ", "")}/videos'
    ]
    
    items = []
    for url in urls_to_try:
        try:
            cmd = ['yt-dlp', '--quiet', '--flat-playlist', '--dump-json', '--playlist-items', '1-15', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0 or not result.stdout.strip():
                continue
            
            # 只检查最新的 5 个视频（按倒序排列）
            video_count = 0
            for line in result.stdout.splitlines():
                if not line.strip() or video_count >= 5:
                    continue
                try:
                    video = json.loads(line)
                except json.JSONDecodeError:
                    continue
                    
                v_id = video.get('id', '')
                if not v_id or is_already_processed(state, v_id):
                    continue
                    
                title = video.get('title', '')
                upload_date = video.get('upload_date', '')
                
                # 如果没有 upload_date，需要单独获取
                if not upload_date:
                    try:
                        date_result = subprocess.run(
                            ['yt-dlp', '--quiet', '--print', 'upload_date', f'https://www.youtube.com/watch?v={v_id}'],
                            capture_output=True, text=True, timeout=30
                        )
                        upload_date = date_result.stdout.strip()
                    except:
                        upload_date = ''
                
                if upload_date and len(upload_date) >= 8:
                    try:
                        video_date = datetime(int(upload_date[:4]), int(upload_date[4:6]), int(upload_date[6:8]))
                        if video_date < cutoff_date:
                            print(f"  ⏭️ 跳过 (超出日期范围): {title[:30]}... ({upload_date})")
                            video_count += 1
                            continue
                        formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                    except ValueError:
                        continue
                else:
                    # 无法获取日期，跳过
                    continue
                
                if include_keywords:
                    if not any(kw.lower() in title.lower() for kw in include_keywords):
                        continue
                
                duration = (video.get('duration') or 0) / 60
                if duration < min_duration:
                    print(f"  ⏭️ 跳过 (时长不足): {title[:30]}... ({round(duration, 1)} 分钟)")
                    video_count += 1
                    continue
                
                items.append({
                    'platform': 'youtube',
                    'channel': name,
                    'title': title,
                    'date': formatted_date,
                    'url': f"https://www.youtube.com/watch?v={v_id}",
                    'id': v_id,
                    'duration': round(duration, 1)
                })
                video_count += 1
            
            if items:
                break  # 成功获取，不再尝试其他 URL
                
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ yt-dlp 超时")
        except Exception as e:
            print(f"  ⚠️ yt-dlp 失败: {e}")
    
    return items

def _get_video_duration(video_id):
    """获取单个视频的时长（分钟）"""
    try:
        result = subprocess.run(
            ['yt-dlp', '--quiet', '--print', 'duration', f'https://www.youtube.com/watch?v={video_id}'],
            capture_output=True, text=True, timeout=30
        )
        duration_sec = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
        return duration_sec / 60
    except:
        return 0

def fetch_xiaoyuzhou_feed(podcast_id, name, min_duration, days, include_keywords, state):
    print(f"正在扫描小宇宙: {name}")
    url = f"https://www.xiaoyuzhoufm.com/podcast/{podcast_id}"
    items = []
    try:
        # 使用 User-Agent 避免被拦截
        headers = ['-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36']
        response = subprocess.run(['curl', '-s', '-L'] + headers + [url], capture_output=True, text=True)
        html = response.stdout
        
        # 提取 ID 映射 (标题 -> ID)
        id_map = {}
        # 更加鲁棒的提取方式：匹配 href 和紧随其后的 title div
        episodes_html = re.findall(r'href="/episode/([a-zA-Z0-9]+)".*?<div[^>]*class="[^"]*title"[^>]*>(.*?)</div>', html, re.DOTALL)
        for eid, title in episodes_html:
            # 去除 HTML 标签（如果有）
            clean_title = re.sub(r'<.*?>', '', title).strip()
            id_map[clean_title] = eid
            
        # 提取 JSON-LD 获取日期
        json_match = re.search(r'<script name="schema:podcast-show" type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            episodes_data = data.get('workExample', [])
            
            for ep in episodes_data:
                title = ep.get('name', '')
                pub_date_str = ep.get('datePublished', '')
                
                # 尝试匹配 ID
                eid = id_map.get(title)
                if not eid:
                    continue
                    
                # ID 去重
                if is_already_processed(state, eid):
                    continue
                
                # 格式化日期 (2026-01-02T10:22:06.258Z -> 2026-01-02)
                formatted_date = pub_date_str[:10] if pub_date_str else datetime.now().strftime('%Y-%m-%d')
                
                # 关键词过滤
                if include_keywords:
                    if not any(kw.lower() in title.lower() for kw in include_keywords):
                        continue
                
                items.append({
                    'platform': 'xiaoyuzhou',
                    'channel': name,
                    'title': title,
                    'date': formatted_date,
                    'url': f"https://www.xiaoyuzhoufm.com/episode/{eid}",
                    'id': eid
                })
        else:
            # 备选方案：如果 JSON-LD 提取失败，回退到原来的逻辑（但日期仍为今天）
            print("警告: 无法提取 JSON-LD，使用备选方案提取列表。")
            for eid, title in episodes_html:
                clean_title = re.sub(r'<.*?>', '', title).strip()
                if is_already_processed(state, eid): continue
                if include_keywords:
                    if not any(kw.lower() in clean_title.lower() for kw in include_keywords): continue
                items.append({
                    'platform': 'xiaoyuzhou',
                    'channel': name,
                    'title': clean_title,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'url': f"https://www.xiaoyuzhoufm.com/episode/{eid}",
                    'id': eid
                })
                
    except Exception as e:
        print(f"获取小宇宙列表失败: {e}")
    
    return items

def main():
    config = load_config()
    state = load_state()
    if not config: return

    settings = config.get('settings', {})
    output_dir = settings.get('output_dir', './content_archive')
    min_duration = settings.get('min_duration_minutes', 30)
    days = settings.get('date_range_days', 7)
    
    all_pending_items = []
    subs = config.get('subscriptions', {})
    
    for yt in subs.get('youtube', []):
        all_pending_items.extend(fetch_youtube_feed(yt['channel_id'], yt['name'], min_duration, days, yt.get('include_keywords'), state))
        
    for xyz in subs.get('xiaoyuzhou', []):
        all_pending_items.extend(fetch_xiaoyuzhou_feed(xyz['podcast_id'], xyz['name'], min_duration, days, xyz.get('include_keywords'), state))
        
    # 文件夹去重
    final_items = []
    for item in all_pending_items:
        if is_folder_exists(output_dir, item['date'], item['platform'], item['channel'], item['title']):
            # 如果文件夹已存在但 ID 不在 state 中，补录 ID
            if item['id'] not in state['processed_ids']:
                state['processed_ids'].append(item['id'])
            continue
        final_items.append(item)
    
    save_state(state)
    
    if not final_items:
        print("\n没有发现新内容。")
        return []

    print(f"\n发现 {len(final_items)} 条新内容:")
    for i, item in enumerate(final_items):
        print(f"{i+1}. [{item['platform'].upper()}] {item['channel']} - {item['title']}")
    
    return final_items

if __name__ == "__main__":
    main()
