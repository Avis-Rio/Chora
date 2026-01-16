import os
import sys
import yaml
import subprocess
import glob
from datetime import datetime
import fetch_feed
from youtube_service import get_youtube_transcript
from rewrite_service import rewrite_content
from generate_cover import generate_cover

# Load Config
def load_config():
    with open('config/sources.yaml', 'r') as f:
        return yaml.safe_load(f)

def load_state():
    if not os.path.exists('config/state.yaml'):
        return {'processed_ids': []}
    with open('config/state.yaml', 'r') as f:
        return yaml.safe_load(f)

def save_state(state):
    with open('config/state.yaml', 'w') as f:
        yaml.safe_dump(state, f)

def download_youtube_thumbnail(video_url, output_dir):
    print(f"Downloading thumbnail for {video_url}...")
    try:
        # Download thumbnail, skip video
        cmd = [
            'yt-dlp', 
            '--write-thumbnail', 
            '--skip-download', 
            '--convert-thumbnails', 'jpg',
            '--output', os.path.join(output_dir, 'cover'),
            video_url
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Check if file exists (yt-dlp adds extension)
        covers = glob.glob(os.path.join(output_dir, 'cover.*'))
        if covers:
            print(f"Thumbnail downloaded: {covers[0]}")
            return covers[0]
        return None
    except Exception as e:
        print(f"Failed to download thumbnail: {e}")
        return None

def process_item(item, config, state):
    print(f"\nProcessing: {item['title']}")
    
    # 1. Create Directory
    safe_title = fetch_feed.get_safe_title(item['title'])
    folder_name = f"{item['platform']}_{item['channel']}_{safe_title}"
    output_dir = os.path.join(config['settings']['output_dir'], item['date'], folder_name)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    # Paths
    transcript_path = os.path.join(output_dir, 'transcript.md')
    metadata_path = os.path.join(output_dir, 'metadata.md')
    rewritten_path = os.path.join(output_dir, 'rewritten.md')
    cover_path = os.path.join(output_dir, 'cover.jpg')

    # 2. Transcript
    transcript_text = None
    if not os.path.exists(transcript_path):
        if item['platform'] == 'youtube':
            transcript_text, lang = get_youtube_transcript(item['id'])
            if transcript_text:
                transcript_text = f"<!-- Language: {lang} -->\n\n{transcript_text}"
        elif item['platform'] == 'xiaoyuzhou':
            # TODO: Implement XiaoYuZhou audio download and transcription
            # For now, we skip or use a placeholder if not implemented
            print("XiaoYuZhou transcription not fully integrated in this script yet.")
            pass
            
        if transcript_text:
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript_text)
            print("Transcript saved.")
        else:
            print("Failed to get transcript. Skipping rewrite.")
            return # Cannot proceed without transcript
    else:
        print("Transcript already exists.")
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

    # 3. Metadata (Simple generation for now, ideally extracted from transcript/feed)
    if not os.path.exists(metadata_path):
        metadata_content = f"""# {item['title']}

## 来源
{item['platform']} ({item['channel']})

## 发布时间
{item['date']}

## 嘉宾
(待提取)

## 金句
(待提取)
"""
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(metadata_content)

    # 4. Cover Image
    # Check if cover exists
    covers = glob.glob(os.path.join(output_dir, 'cover.*'))
    if not covers:
        if item['platform'] == 'youtube':
            # Try downloading
            downloaded_cover = download_youtube_thumbnail(item['url'], output_dir)
            if not downloaded_cover:
                # Fallback to Gemini
                print("Thumbnail download failed. Generating cover with Gemini...")
                prompt = f"Design a professional 16:9 cover image for a content summary. Title: '{item['title']}'. Style: Artistic, professional, inspiring. Do NOT include channel names."
                generate_cover(prompt, cover_path)
        else:
            # XiaoYuZhou: Try to get cover from feed (not implemented in fetch_feed yet), or generate
            print("Generating cover with Gemini...")
            prompt = f"Design a professional 16:9 cover image for a podcast summary. Title: '{item['title']}'. Style: Artistic, professional, inspiring. Do NOT include channel names."
            generate_cover(prompt, cover_path)
    else:
        print(f"Cover image exists: {covers[0]}")

    # 5. Rewrite
    if not os.path.exists(rewritten_path) and transcript_text:
        success = rewrite_content(transcript_path, metadata_path, rewritten_path)
        if success:
            print("Rewrite completed.")
            
            # 6. Update State
            if item['id'] not in state['processed_ids']:
                state['processed_ids'].append(item['id'])
                save_state(state)
                print(f"Marked {item['id']} as processed.")

def main():
    # 1. Fetch Feed
    print("Fetching feed...")
    items = fetch_feed.main() # This prints items and returns them
    
    if not items:
        print("No new items found.")
        return

    # 2. Confirm
    response = input(f"\nFound {len(items)} new items. Start processing? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        return

    # 3. Process
    config = load_config()
    state = load_state()
    
    for item in items:
        try:
            process_item(item, config, state)
        except Exception as e:
            print(f"Error processing {item['title']}: {e}")
            continue

if __name__ == "__main__":
    main()
