import os
import glob
import re
import subprocess
import json
from youtube_transcript_api import YouTubeTranscriptApi

def clean_vtt_text(vtt_content):
    """
    Parses YouTube VTT content and extracts plain text.
    Removes timestamps, tags, and handles duplicate lines common in YouTube captions.
    """
    lines = vtt_content.split('\n')
    text_lines = []

    # Regex for timestamp line (e.g., 00:00:00.240 --> 00:00:02.070)
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}\.\d{3}\s-->\s\d{2}:\d{2}:\d{2}\.\d{3}')

    for line in lines:
        line = line.strip()
        # Skip empty lines, headers, and timestamps
        if not line:
            continue
        if line == 'WEBVTT' or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        if timestamp_pattern.match(line):
            continue

        # Remove HTML-like tags (e.g., <c>, <00:00:00.560>)
        clean_line = re.sub(r'<[^>]+>', '', line)
        clean_line = clean_line.strip()

        # Skip empty after cleaning
        if not clean_line:
            continue

        # Basic deduplication for rolling captions
        if text_lines and text_lines[-1] == clean_line:
            continue

        text_lines.append(clean_line)

    return " ".join(text_lines)


def get_video_metadata(video_id):
    """
    使用 yt-dlp 获取视频元数据（标题、发布日期、频道等）
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--skip-download',
            video_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # 提取关键元数据
        metadata = {
            'title': data.get('title', ''),
            'channel': data.get('channel', data.get('uploader', '')),
            'upload_date': data.get('upload_date', ''),  # 格式: YYYYMMDD
            'description': data.get('description', '')[:500],  # 只取前500字符
            'duration': data.get('duration', 0),
            'view_count': data.get('view_count', 0),
        }
        
        # 格式化日期 YYYYMMDD -> YYYY-MM-DD
        if metadata['upload_date'] and len(metadata['upload_date']) == 8:
            d = metadata['upload_date']
            metadata['upload_date'] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        
        print(f"Video metadata retrieved: {metadata['title']}")
        print(f"  Upload date: {metadata['upload_date']}")
        print(f"  Channel: {metadata['channel']}")

        return metadata
    except Exception as e:
        print(f"Failed to get video metadata: {e}")
        return None


def download_cover(video_id, output_dir):
    """
    Downloads the best available thumbnail for the video using yt-dlp.
    """
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        print(f"Downloading cover for {video_id}...")
        cmd = [
            'yt-dlp',
            '--write-thumbnail',
            '--skip-download',
            '--convert-thumbnails', 'jpg',
            '--output', f'{output_dir}/cover.%(ext)s',
            video_url
        ]
        # Run yt-dlp
        subprocess.run(cmd, check=True, capture_output=True)

        # Verify file exists
        if os.path.exists(f"{output_dir}/cover.jpg"):
            print(f"✅ Cover image saved to {output_dir}/cover.jpg")
            return True
        else:
            print("⚠️ Cover download completed but file not found (maybe failed to convert?)")
            return False

    except Exception as e:
        print(f"❌ Failed to download cover: {e}")
        return False


def get_youtube_transcript(video_id):
    """
    Fetches the transcript for a YouTube video using youtube-transcript-api.
    优先获取中文字幕，如果没有则尝试翻译英文字幕为中文。
    """
    print(f"Fetching transcript for video ID: {video_id}")
    
    try:
        yt_api = YouTubeTranscriptApi()
        
        # 第一步：列出所有可用字幕
        print("Listing available transcripts...")
        transcript_list = yt_api.list(video_id)
        
        available_langs = []
        translatable_transcript = None
        chinese_transcript = None
        
        for t in transcript_list:
            lang_info = f"{t.language} ({t.language_code})"
            if t.is_generated:
                lang_info += " [auto-generated]"
            if t.is_translatable:
                lang_info += " [translatable]"
            available_langs.append(lang_info)
            print(f"  Found: {lang_info}")
            
            # 检查是否有中文字幕
            if t.language_code in ['zh-Hans', 'zh-Hant', 'zh', 'zh-CN', 'zh-TW']:
                chinese_transcript = t
            
            # 记录可翻译的字幕（优先英文）
            if t.is_translatable and t.language_code == 'en':
                translatable_transcript = t
            elif t.is_translatable and not translatable_transcript:
                translatable_transcript = t
        
        # 第二步：优先使用中文字幕
        if chinese_transcript:
            print(f"Using Chinese transcript: {chinese_transcript.language}")
            fetched = chinese_transcript.fetch()
            full_text = ""
            for snippet in fetched:
                full_text += snippet.text + " "
            print(f"Fetched {len(fetched)} snippets in Chinese.")
            return full_text, chinese_transcript.language_code
        
        # 第三步：如果没有中文，尝试翻译
        if translatable_transcript:
            print(f"No Chinese transcript found. Translating from {translatable_transcript.language} to Chinese...")
            try:
                translated = translatable_transcript.translate('zh-Hans')
                fetched = translated.fetch()
                full_text = ""
                for snippet in fetched:
                    full_text += snippet.text + " "
                print(f"Successfully translated {len(fetched)} snippets to Chinese.")
                return full_text, 'zh-Hans (translated)'
            except Exception as e:
                print(f"Translation failed: {e}")
                # 如果翻译失败，回退到原语言
                print(f"Falling back to original language: {translatable_transcript.language}")
                fetched = translatable_transcript.fetch()
                full_text = ""
                for snippet in fetched:
                    full_text += snippet.text + " "
                return full_text, translatable_transcript.language_code
        
        # 第四步：如果都不行，尝试直接 fetch
        print("No translatable transcript found. Attempting direct fetch...")
        try:
            fetched = yt_api.fetch(video_id, languages=['zh-Hans', 'zh-Hant', 'zh', 'en'])
            full_text = ""
            for snippet in fetched:
                full_text += snippet.text + " "
            return full_text, fetched.language_code
        except Exception as e:
            print(f"Direct fetch failed: {e}")
            return None, None
            
    except Exception as e:
        print(f"Failed to get transcript: {e}")
        return None, None


if __name__ == "__main__":
    # Test with the Kevin Kelly video
    vid = "8uHur4G1ZVI"
    
    # Test metadata
    print("=== Testing Video Metadata ===")
    metadata = get_video_metadata(vid)
    if metadata:
        print(f"Title: {metadata['title']}")
        print(f"Date: {metadata['upload_date']}")
        print(f"Channel: {metadata['channel']}")
    
    # Test transcript
    print("\n=== Testing Transcript ===")
    transcript, lang = get_youtube_transcript(vid)
    if transcript:
        print(f"\nLanguage: {lang}")
        print(f"Transcript length: {len(transcript)} characters")
        print(f"\n--- First 500 chars ---")
        print(transcript[:500] + "...")
    else:
        print("Failed to extract transcript.")
