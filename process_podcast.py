import os
import sys
# 确保 Python 用户安装目录和 Homebrew 目录在 PATH 中
py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
user_bin = os.path.expanduser(f'~/Library/Python/{py_version}/bin')
brew_bin = '/opt/homebrew/bin'
local_bin = '/usr/local/bin'
os.environ['PATH'] = f'{user_bin}:{brew_bin}:{local_bin}:{os.environ.get("PATH", "")}'
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
from datetime import datetime
from groq import Groq
import glob
import rewrite_service
from config_loader import load_sources_config
from generate_cover import generate_podcast_cover
from distribution_pipeline.automation import generate_distribution_after_rewrite
from xiaoyuzhou_service import get_episode_metadata, extract_episode_id

def load_config():
    return load_sources_config('config/sources.yaml')

def sanitize_filename(name):
    """Sanitize string to be safe for filenames."""
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = name.replace(' ', '_')
    return name[:50]

def get_episode_metadata_wrapper(url_or_id):
    """Thin wrapper around xiaoyuzhou_service for dict compatibility."""
    try:
        meta = get_episode_metadata(url_or_id)
        return {
            'title': meta.title,
            'channel': meta.channel,
            'upload_date': meta.upload_date,
            'audio_url': meta.audio_url,
            'episode_id': meta.episode_id,
            'guests': meta.guests,
            'description': meta.description,
            'source_url': meta.source_url,
        }
    except Exception as exc:
        print(f"Error fetching metadata: {exc}")
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
        
        min_size = 100 * 1024  # 100KB minimum size for valid audio
        if os.path.exists(output_path) and os.path.getsize(output_path) > min_size:
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✅ Audio downloaded: {file_size_mb:.1f} MB")
            return True
        else:
            actual_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            print(f"❌ Download failed or file too small ({actual_size} bytes < 100KB). Likely invalid/protected source.")
            if result.stderr:
                print(f"stderr: {result.stderr[:200]}")
            # Clean up invalid file
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
    except subprocess.TimeoutExpired:
        print("Error: Download timed out after 10 minutes.")
        return False
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return False

def split_audio(file_path, chunk_length_sec=300):  # 5分钟一片
    """Split audio into chunks using ffmpeg."""
    print("Splitting audio file using ffmpeg...")
    
    # Clean up any existing temp chunks
    for f in glob.glob("temp_chunk_*.mp3"):
        os.remove(f)
        
    output_pattern = "temp_chunk_%03d.mp3"
    
    try:
        # Use ffmpeg to split
        # -i input -f segment -segment_time 300 -c:a libmp3lame -q:a 4 output_pattern
        # Using re-encoding to ensure consistent format and avoid boundary issues, 
        # but -c copy is faster if source is mp3. Let's use libmp3lame to be safe and standard.
        cmd = [
            'ffmpeg', '-i', file_path,
            '-f', 'segment',
            '-segment_time', str(chunk_length_sec),
            '-c:a', 'libmp3lame',
            '-q:a', '4',  # Reasonable quality
            '-loglevel', 'error',
            output_pattern
        ]
        
        subprocess.run(cmd, check=True)
        
        # Get list of generated files
        chunks = sorted(glob.glob("temp_chunk_*.mp3"))
        print(f"Audio split into {len(chunks)} chunks.")
        return chunks
        
    except subprocess.CalledProcessError as e:
        print(f"Error splitting audio: {e}")
        return []

import time

def transcribe_chunk(client, chunk_filename, index):
    """Transcribe a single audio chunk file using Groq Whisper with retry on 429."""
    print(f"  Transcribing {chunk_filename}...")
    max_retries = 12
    
    for attempt in range(max_retries):
        try:
            with open(chunk_filename, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(chunk_filename, file.read()),
                    model="whisper-large-v3",
                    response_format="text",
                    timeout=300.0
                )
            return transcription
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                # Default backoff
                wait_time = 60 * (1.5 ** attempt) # Start at 60s, then 90, 135...
                
                # Try to parse specific wait time from Groq error message
                # e.g. "Please try again in 2m24s" or "try again in 1m36.5s"
                match = re.search(r'try again in (\d+)m([\d.]+)s', error_str)
                if match:
                    wait_time = int(match.group(1)) * 60 + float(match.group(2)) + 5
                else:
                    match_s = re.search(r'try again in ([\d.]+)s', error_str)
                    if match_s:
                        wait_time = float(match_s.group(1)) + 5
                
                # Cap wait time to 15 mins
                wait_time = min(wait_time, 900)
                
                print(f"  ⚠️ Rate limit hit (429) on {chunk_filename}. Retrying in {wait_time:.1f}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                print(f"Error transcribing {chunk_filename}: {e}")
                raise e
    
    raise Exception(f"Failed to transcribe {chunk_filename} after {max_retries} retries due to rate limits.")

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
    # Reduced workers to be less aggressive with rate limits
    max_workers = 3  
    results = [None] * len(chunks)
    
    print(f"🚀 Starting parallel transcription with {max_workers} workers...")
    
    import concurrent.futures
    
    try:
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
                    # Clean up the chunk file after successful processing
                    chunk_filename = f"temp_chunk_{index:03d}.mp3"
                    if os.path.exists(chunk_filename):
                        os.remove(chunk_filename)
                except Exception as e:
                    print(f"  ❌ Chunk {index+1}/{len(chunks)} failed permanently: {e}")
                    results[index] = f"[Chunk {index+1} transcription failed]"
    except KeyboardInterrupt:
        print("\nStopping transcription...")
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    
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
    metadata = get_episode_metadata_wrapper(episode_id)
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
    
    if os.path.exists(rewritten_path):
        print("Rewritten content already exists, skipping rewrite.")
        success = True
    else:
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
            output_path=cover_path,
            content_path=rewritten_path
        )
        if not cover_success:
            print("⚠️ Cover generation failed, but continuing...")
    
    distribution_dir = generate_distribution_after_rewrite(output_dir, context="process_podcast")

    print(f"\n✅ Processing Complete! Output in: {output_dir}")
    print(f"   - Metadata: {metadata_path}")
    print(f"   - Transcript: {transcript_path}")
    print(f"   - Rewritten: {rewritten_path}")
    if os.path.exists(cover_path):
        print(f"   - Cover: {cover_path}")
    if distribution_dir:
        print(f"   - Distribution: {distribution_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_podcast.py <xiaoyuzhou_url>")
        print("Example: python3 process_podcast.py https://www.xiaoyuzhoufm.com/episode/5e4ff46a418a84a046973eee")
        sys.exit(1)
    
    process_podcast(sys.argv[1])
