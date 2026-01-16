import os
import sys
import argparse
import re
from datetime import datetime
import youtube_service
import rewrite_service

def sanitize_filename(name):
    """Sanitize string to be safe for filenames."""
    # Remove invalid characters
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Limit length
    return name[:50]

def process_video(video_id_or_url):
    """
    Full workflow for processing a YouTube video:
    1. Get metadata
    2. Create archive folder
    3. Download cover
    4. Get transcript
    5. Run AI rewrite
    """
    # Extract video ID if full URL is provided
    video_id = video_id_or_url
    if "youtube.com" in video_id or "youtu.be" in video_id:
        if "v=" in video_id:
            video_id = video_id.split("v=")[1].split("&")[0]
        else:
            # Handle youtu.be/ID format
            video_id = video_id.split("/")[-1]

    print(f"🚀 Processing YouTube Video ID: {video_id}")

    # 1. Get Metadata
    print("\n[1/5] Fetching Metadata...")
    metadata = youtube_service.get_video_metadata(video_id)
    if not metadata:
        print("❌ Failed to get metadata. Aborting.")
        return

    # 2. Create Archive Folder
    print("\n[2/5] Creating Archive Folder...")
    date_str = metadata['upload_date'] # YYYY-MM-DD
    safe_title = sanitize_filename(metadata['title'])
    safe_channel = sanitize_filename(metadata['channel'])

    content_folder = f"youtube_{safe_channel}_{safe_title}"
    output_dir = os.path.join("content_archive", date_str, content_folder)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    else:
        print(f"Directory exists: {output_dir}")

    # Save initial metadata (will be updated by AI with 嘉宾 and 金句)
    metadata_path = os.path.join(output_dir, "metadata.md")
    source_url = f"https://www.youtube.com/watch?v={video_id}"
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
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(initial_metadata)
        print("Saved initial metadata.md")

    # 3. Download Cover
    print("\n[3/5] Downloading Cover...")
    youtube_service.download_cover(video_id, output_dir)

    # 4. Get Transcript
    print("\n[4/5] Fetching Transcript...")
    transcript_path = os.path.join(output_dir, "transcript.md")

    if os.path.exists(transcript_path):
        print("Transcript already exists, skipping fetch.")
    else:
        transcript_text, lang = youtube_service.get_youtube_transcript(video_id)
        if transcript_text:
            with open(transcript_path, "w", encoding="utf-8") as f:
                f.write(transcript_text)
            print(f"Saved transcript ({len(transcript_text)} chars) to {transcript_path}")
        else:
            print("❌ Failed to get transcript. Aborting rewrite.")
            return

    # 5. Run AI Rewrite
    print("\n[5/5] Running AI Rewrite...")
    rewritten_path = os.path.join(output_dir, "rewritten.md")

    success = rewrite_service.rewrite_content(transcript_path, metadata_path, rewritten_path)

    if success:
        print(f"\n✅ Processing Complete! Output in: {output_dir}")
        print(f"   - Metadata: {metadata_path}")
        print(f"   - Rewritten: {rewritten_path}")
    else:
        print("\n❌ Rewrite failed.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_video.py <video_id_or_url>")
        sys.exit(1)

    process_video(sys.argv[1])
