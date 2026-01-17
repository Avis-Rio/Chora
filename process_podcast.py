"""
小宇宙播客处理器
处理单个小宇宙播客 URL 的完整工作流

用法: python3 process_podcast.py <xiaoyuzhou_url>
示例: python3 process_podcast.py https://www.xiaoyuzhoufm.com/episode/5e4ff46a418a84a046973eee
"""

import os
import sys
import re
import json
import subprocess
import yaml
from datetime import datetime
from groq import Groq
from pydub import AudioSegment
import rewrite_service
from generate_cover import generate_podcast_cover

def load_config():
    with open('config/sources.yaml', 'r') as f:
        return yaml.safe_load(f)

def sanitize_filename(name):
    """Sanitize string to be safe for filenames."""
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = name.replace(' ', '_')
    return name[:50]

def extract_episode_id(url):
    """Extract episode ID from xiaoyuzhou URL."""
    match = re.search(r'/episode/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None

def get_episode_metadata(episode_id):
    """Fetch episode metadata from xiaoyuzhou page."""
    url = f"https://www.xiaoyuzhoufm.com/episode/{episode_id}"
    print(f"Fetching metadata from {url}...")
    
    try:
        headers = ['-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36']
        result = subprocess.run(['curl', '-s', '-L'] + headers + [url], capture_output=True, text=True)
        html = result.stdout
        
        # Try to extract from __NEXT_DATA__ (contains more detailed info including description)
        next_data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        description = ""
        guests = ""
        
        if next_data_match:
            try:
                next_data = json.loads(next_data_match.group(1))
                episode = next_data.get('props', {}).get('pageProps', {}).get('episode', {})
                description = episode.get('description', '')
                
                # Extract guests from description
                guests = extract_guests_from_description(description)
                if guests:
                    print(f"  Extracted guests: {guests[:50]}...")
            except:
                pass
        
        # Extract JSON-LD data (小宇宙使用 schema:podcast-show 但包含 PodcastEpisode 数据)
        json_match = re.search(r'<script name="schema:podcast-show" type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            
            title = data.get('name', 'Unknown Episode')
            pub_date_raw = data.get('datePublished', '')
            pub_date = pub_date_raw[:10] if pub_date_raw else datetime.now().strftime('%Y-%m-%d')
            
            # Audio URL 在 associatedMedia.contentUrl 中
            audio_url = data.get('associatedMedia', {}).get('contentUrl', '')
            
            # 频道名在 partOfSeries.name 中
            channel = data.get('partOfSeries', {}).get('name', 'Unknown')
            
            return {
                'title': title,
                'channel': channel,
                'upload_date': pub_date,
                'audio_url': audio_url,
                'episode_id': episode_id,
                'guests': guests,  # 新增嘉宾字段
                'description': description  # 保留描述用于 AI 参考
            }
        
        # Fallback: extract from HTML title tag
        title_match = re.search(r'<title>(.*?)</title>', html)
        title = title_match.group(1) if title_match else 'Unknown Episode'
        
        return {
            'title': title,
            'channel': 'Unknown',
            'upload_date': datetime.now().strftime('%Y-%m-%d'),
            'audio_url': '',
            'episode_id': episode_id,
            'guests': guests,
            'description': description
        }
        
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return None


def extract_guests_from_description(description):
    """从小宇宙节目描述中提取嘉宾信息。
    
    常见格式：
    - "本期话题成员 -\n嘉宾1，简介\n嘉宾2，简介"
    - "嘉宾：xxx"
    - "本期嘉宾：xxx"
    """
    if not description:
        return ""
    
    guests_lines = []
    
    # 模式1：查找 "本期话题成员" 或 "本期嘉宾" 部分
    patterns = [
        r'[-–—]\s*本期话题成员\s*[-–—]\s*\n(.*?)(?=\n[-–—]|\n\n|\Z)',
        r'[-–—]\s*嘉宾\s*[-–—]\s*\n(.*?)(?=\n[-–—]|\n\n|\Z)',
        r'本期嘉宾[：:]\s*(.*?)(?=\n\n|\Z)',
        r'嘉宾[：:]\s*(.*?)(?=\n\n|\Z)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # 按行分割，每行是一个嘉宾
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            # 过滤掉时间轴等无关内容
            for line in lines:
                # 跳过时间轴格式 (如 "01:58 xxx")
                if re.match(r'^\d{1,2}:\d{2}', line):
                    break
                # 跳过空行和分隔符
                if line.startswith('-') and len(line) < 5:
                    continue
                guests_lines.append(line)
            
            if guests_lines:
                break
    
    return '\n'.join(guests_lines)

def download_audio(audio_url, output_path):
    """Download audio file from URL."""
    print(f"Downloading audio from: {audio_url[:60]}...")
    print(f"Saving to: {output_path}")
    try:
        result = subprocess.run([
            'curl', '-L', 
            '-o', output_path,
            '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            '--max-time', '600',  # 10分钟超时
            '--progress-bar',
            audio_url
        ], capture_output=True, text=True, timeout=660)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ Audio downloaded: {file_size_mb:.1f} MB")
            return True
        else:
            print(f"Download failed. stderr: {result.stderr[:200] if result.stderr else 'None'}")
            return False
    except subprocess.TimeoutExpired:
        print("Error: Download timed out after 10 minutes.")
        return False
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return False

def split_audio(file_path, chunk_length_ms=300000):  # 5分钟一片
    """Split audio into chunks for transcription."""
    print("Loading audio file...")
    audio = AudioSegment.from_file(file_path)
    chunks = []
    print(f"Audio duration: {len(audio)/1000/60:.2f} minutes")
    for i in range(0, len(audio), chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunks.append(chunk)
    return chunks

def transcribe_chunk(client, chunk, index):
    """Transcribe a single audio chunk using Groq Whisper."""
    temp_filename = f"temp_chunk_{index}.mp3"
    chunk.export(temp_filename, format="mp3")
    
    try:
        with open(temp_filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(temp_filename, file.read()),
                model="whisper-large-v3",
                response_format="text",
                timeout=300.0
            )
        return transcription
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

def transcribe_audio(audio_path, config):
    """Transcribe audio file using Groq Whisper API with parallel processing."""
    api_key = config.get('api_keys', {}).get('groq')
    if not api_key:
        print("Error: Groq API key not found in config.")
        return None
    
    # Create a client factory or shared client
    # Groq client is generally thread-safe for requests
    client = Groq(api_key=api_key)
    
    print("Splitting audio for transcription...")
    chunks = split_audio(audio_path)
    print(f"Audio split into {len(chunks)} chunks.")
    
    # Parallel processing configuration
    max_workers = 5  # Process 5 chunks in parallel
    results = [None] * len(chunks)
    
    print(f"🚀 Starting parallel transcription with {max_workers} workers...")
    
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(transcribe_chunk, client, chunk, i): i 
            for i, chunk in enumerate(chunks)
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                transcript = future.result()
                results[index] = transcript
                print(f"  ✅ Chunk {index+1}/{len(chunks)} completed")
            except Exception as e:
                print(f"  ❌ Chunk {index+1}/{len(chunks)} failed: {e}")
                results[index] = f"[Chunk {index+1} transcription failed]"
    
    # Combine results in order
    full_transcript = "\n".join(filter(None, results))
    return full_transcript

def process_podcast(podcast_url):
    """
    Full workflow for processing a xiaoyuzhou podcast episode:
    1. Get metadata
    2. Create archive folder
    3. Download audio
    4. Transcribe audio
    5. Run AI rewrite
    6. Generate cover image
    """
    # Extract episode ID
    episode_id = extract_episode_id(podcast_url)
    if not episode_id:
        print("❌ Invalid xiaoyuzhou URL. Expected format: https://www.xiaoyuzhoufm.com/episode/XXXX")
        return
    
    print(f"🚀 Processing Xiaoyuzhou Episode ID: {episode_id}")
    
    # 1. Get Metadata
    print("\n[1/5] Fetching Metadata...")
    metadata = get_episode_metadata(episode_id)
    if not metadata:
        print("❌ Failed to get metadata. Aborting.")
        return
    
    print(f"  Title: {metadata['title']}")
    print(f"  Channel: {metadata['channel']}")
    print(f"  Date: {metadata['upload_date']}")
    
    # 2. Create Archive Folder (使用修复后的格式: {date}/{platform}_{channel}_{title})
    print("\n[2/5] Creating Archive Folder...")
    date_str = metadata['upload_date']
    safe_title = sanitize_filename(metadata['title'])
    safe_channel = sanitize_filename(metadata['channel'])
    
    content_folder = f"xiaoyuzhou_{safe_channel}_{safe_title}"
    output_dir = os.path.join("content_archive", date_str, content_folder)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    else:
        print(f"Directory exists: {output_dir}")
    
    # Save initial metadata (包含从页面提取的嘉宾信息)
    metadata_path = os.path.join(output_dir, "metadata.md")
    source_url = f"https://www.xiaoyuzhoufm.com/episode/{episode_id}"
    if not os.path.exists(metadata_path):
        # 标准 metadata 格式：来源只包含频道名
        initial_metadata = f"""# {metadata['title']}

## 来源
{metadata['channel']}

## 原始链接
{source_url}

## 发布时间
{metadata['upload_date']}
"""
        # 如果提取到嘉宾信息，直接写入 metadata（而非依赖 AI 推断）
        if metadata.get('guests'):
            initial_metadata += f"""
## 嘉宾
{metadata['guests']}
"""
            print(f"  Saved extracted guests to metadata.md")
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(initial_metadata)
        print("Saved initial metadata.md")
    
    # Load config
    config = load_config()
    
    # 3. Download Audio
    print("\n[3/5] Downloading Audio...")
    audio_path = os.path.join(output_dir, "audio.m4a")
    
    if os.path.exists(audio_path):
        print("Audio already exists, skipping download.")
    else:
        if metadata.get('audio_url'):
            success = download_audio(metadata['audio_url'], audio_path)
            if not success:
                print("❌ Failed to download audio. Aborting.")
                return
        else:
            print("❌ No audio URL found. Aborting.")
            return
    
    # 4. Transcribe Audio
    print("\n[4/5] Transcribing Audio...")
    transcript_path = os.path.join(output_dir, "transcript.md")
    
    if os.path.exists(transcript_path):
        print("Transcript already exists, skipping transcription.")
    else:
        transcript_text = transcribe_audio(audio_path, config)
        if transcript_text:
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript_text)
            print(f"Saved transcript ({len(transcript_text)} chars)")
        else:
            print("❌ Transcription failed. Aborting rewrite.")
            return
    
    # 5. Run AI Rewrite
    print("\n[5/6] Running AI Rewrite...")
    rewritten_path = os.path.join(output_dir, "rewritten.md")
    
    success = rewrite_service.rewrite_content(transcript_path, metadata_path, rewritten_path)
    
    if not success:
        print("\n❌ Rewrite failed.")
        return
    
    # 6. Generate Cover Image
    print("\n[6/6] Generating Cover Image...")
    cover_path = os.path.join(output_dir, "cover.png")
    
    if os.path.exists(cover_path):
        print("Cover already exists, skipping generation.")
    else:
        cover_success = generate_podcast_cover(
            title=metadata['title'],
            channel=metadata['channel'],
            output_path=cover_path
        )
        if not cover_success:
            print("⚠️ Cover generation failed, but continuing...")
    
    print(f"\n✅ Processing Complete! Output in: {output_dir}")
    print(f"   - Metadata: {metadata_path}")
    print(f"   - Transcript: {transcript_path}")
    print(f"   - Rewritten: {rewritten_path}")
    if os.path.exists(cover_path):
        print(f"   - Cover: {cover_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_podcast.py <xiaoyuzhou_url>")
        print("Example: python3 process_podcast.py https://www.xiaoyuzhoufm.com/episode/5e4ff46a418a84a046973eee")
        sys.exit(1)
    
    process_podcast(sys.argv[1])
