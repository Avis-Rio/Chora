#!/usr/bin/env python3
"""
Export content archive to JSON format for Feishu integration.
Scans content_archive directory and generates structured JSON files.
"""

import os
import sys
import json
import re
import glob
from datetime import datetime

def extract_metadata(metadata_path):
    """Extract metadata from metadata.md file."""
    if not os.path.exists(metadata_path):
        return {}
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    metadata = {}
    
    # Extract title (first line starting with #)
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        metadata['title'] = title_match.group(1).strip()
    
    # Extract source
    source_match = re.search(r'##\s+来源\s*\n(.+)', content)
    if source_match:
        source = source_match.group(1).strip()
        # Clean channel name
        clean_channel = source
        for prefix in ['YouTube - ', '小宇宙 - ', 'YouTube ', '小宇宙 ']:
            clean_channel = clean_channel.replace(prefix, '')
        # Remove platform in brackets if present e.g. "Channel (YouTube)"
        clean_channel = re.sub(r'\s*[\(（](YouTube|小宇宙|Podcast)[\)）]', '', clean_channel, flags=re.IGNORECASE)
        
        metadata['channel'] = clean_channel.strip()
        
        if 'YouTube' in source:
            metadata['platform'] = 'youtube'
        elif '小宇宙' in source:
            metadata['platform'] = 'xiaoyuzhou'
    
    # Extract source URL
    url_match = re.search(r'##\s+原始链接\s*\n(.+)', content)
    if url_match:
        metadata['source_url'] = url_match.group(1).strip()
    
    # Extract publish date
    date_match = re.search(r'##\s+发布时间\s*\n(\d{4}-\d{2}-\d{2})', content)
    if date_match:
        metadata['publish_date'] = date_match.group(1)
    
    # Extract guests
    guest_match = re.search(r'##\s+嘉宾\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if guest_match:
        metadata['guests'] = guest_match.group(1).strip()
    
    # Extract quotes - stricter extraction
    # Only look for quotes in the "金句" section
    quotes_section = re.search(r'##\s+金句\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if quotes_section:
        section_content = quotes_section.group(1)
        # Extract lines starting with >
        quotes = re.findall(r'>\s*(.+)', section_content)
        # Filter out markdown headers if any slipped in
        quotes = [q for q in quotes if not q.strip().startswith('#')]
        if quotes:
            metadata['quotes'] = quotes
    
    return metadata

def extract_rewritten(rewritten_path):
    """Extract rewritten content and structured data."""
    if not os.path.exists(rewritten_path):
        return {}
    
    with open(rewritten_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = {
        'rewritten': content,
        'word_count': len(content)
    }
    
    # Extract score
    # Handle formats like [100] or [108/120]
    score_match = re.search(r'总分\s*\[(\d+)(?:/\d+)?\]', content)
    if score_match:
        data['score'] = int(score_match.group(1))
    
    # Extract summary (first paragraph of deep rewrite section)
    summary_match = re.search(r'##\s*2\.\s*深度改写.*?\n\n(.+?)(?=\n\n)', content, re.DOTALL)
    if summary_match:
        summary = summary_match.group(1).strip()
        # Limit to ~150 chars
        if len(summary) > 150:
            summary = summary[:147] + '...'
        data['summary'] = summary
    
    # Estimate reading time (Chinese: ~400 chars/min)
    data['reading_time'] = max(1, round(len(content) / 400))
    
    # Extract book list section
    book_section = re.search(r'##\s*5\.\s*推荐书单.*?\n\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if book_section:
        data['book_list'] = book_section.group(1).strip()
    
    # Extract tags (support both Chinese and English formats)
    tags_match = re.search(r'(?:标签|Tags)[:：]\s*(.+)', content, re.IGNORECASE)
    if tags_match:
        tags_str = tags_match.group(1).strip()
        # Parse comma-separated tags
        tags = [t.strip() for t in re.split(r'[,，、]', tags_str) if t.strip()]
        data['tags'] = tags
    else:
        data['tags'] = []
    
    return data

def generate_id(folder_name, platform, metadata=None):
    """Generate unique ID, preferring real source ID."""
    
    # 1. Try to get ID from source_url
    if metadata and metadata.get('source_url'):
        url = metadata['source_url']
        if 'youtube.com/watch' in url or 'youtu.be/' in url:
            # Extract v=VIDEO_ID
            vid_match = re.search(r'v=([a-zA-Z0-9_-]{11})', url)
            if vid_match:
                return vid_match.group(1)
            # Short URL
            vid_match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url)
            if vid_match:
                return vid_match.group(1)
        elif 'xiaoyuzhoufm.com/episode/' in url:
            eid_match = re.search(r'episode/([a-f0-9]{24})', url)
            if eid_match:
                return eid_match.group(1)

    # 2. Try to extract ID from folder name (if it contains ID)
    # YouTube ID is usually 11 chars, Xiaoyuzhou is 24 hex chars
    if platform == 'xiaoyuzhou':
        # Check for 24-char hex ID
        id_match = re.search(r'[a-f0-9]{24}', folder_name)
        if id_match:
            return id_match.group(0)
    elif platform == 'youtube':
        # YouTube IDs are harder to distinguish from text, but usually at the end or beginning
        # If we can't find it in URL, we might fallback to hash
        pass
    
    # 3. Fallback to sanitized folder name (legacy behavior)
    clean_name = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fa5]', '', folder_name)[:30]
    prefix = 'yt' if platform == 'youtube' else 'xyz'
    return f"{prefix}_{clean_name}"

def export_folder(folder_path):
    """Export a single content folder to JSON."""
    folder_name = os.path.basename(folder_path)
    
    # Read metadata
    metadata_path = os.path.join(folder_path, 'metadata.md')
    metadata = extract_metadata(metadata_path)
    
    if not metadata:
        print(f"  ⚠️ No metadata found, skipping")
        return None
    
    # Read rewritten content
    rewritten_path = os.path.join(folder_path, 'rewritten.md')
    rewritten_data = extract_rewritten(rewritten_path)
    
    # Determine platform
    platform = metadata.get('platform', 'unknown')
    if 'youtube_' in folder_name:
        platform = 'youtube'
    elif 'xiaoyuzhou_' in folder_name:
        platform = 'xiaoyuzhou'
    
    # Try to recover source_url if missing
    if not metadata.get('source_url'):
        # Try info.json
        info_path = os.path.join(folder_path, 'info.json')
        if os.path.exists(info_path):
            try:
                with open(info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    if info.get('webpage_url'):
                        metadata['source_url'] = info['webpage_url']
            except:
                pass
        
        # Try to reconstruct from folder name (if ID is present)
        if not metadata.get('source_url'):
            if platform == 'xiaoyuzhou':
                eid_match = re.search(r'[a-f0-9]{24}', folder_name)
                if eid_match:
                    metadata['source_url'] = f"https://www.xiaoyuzhoufm.com/episode/{eid_match.group(0)}"
    
    # Check for cover
    cover_path = None
    for ext in ['png', 'jpg', 'jpeg']:
        potential = os.path.join(folder_path, f'cover.{ext}')
        if os.path.exists(potential):
            cover_path = potential
            break
    
    # Read transcript
    transcript_path = os.path.join(folder_path, 'transcript.md')
    transcript = ''
    if os.path.exists(transcript_path):
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript = f.read()
    
    # Build export data
    export_data = {
        'id': generate_id(folder_name, platform, metadata),
        'title': metadata.get('title', folder_name),
        'source_url': metadata.get('source_url', ''),
        'platform': platform,
        'channel': metadata.get('channel', 'Unknown'),
        'publish_date': metadata.get('publish_date', ''),
        'cover_path': cover_path,
        'summary': rewritten_data.get('summary', ''),
        'reading_time': rewritten_data.get('reading_time', 0),
        'score': rewritten_data.get('score', 0),
        'tags': rewritten_data.get('tags', []),
        'quotes': metadata.get('quotes', []),
        'book_list': rewritten_data.get('book_list', ''),
        'rewritten': rewritten_data.get('rewritten', ''),
        'transcript': transcript,
        'word_count': rewritten_data.get('word_count', 0),
        'guests': metadata.get('guests', ''),
        'folder_path': folder_path,
        'exported_at': datetime.now().isoformat()
    }
    
    return export_data

def export_all(output_path='content_export.json'):
    """Export all content from content_archive to JSON."""
    archive_dir = 'content_archive'
    
    if not os.path.exists(archive_dir):
        print(f"❌ Archive directory not found: {archive_dir}")
        return
    
    all_content = []
    
    # Find all content folders
    for date_dir in sorted(glob.glob(f'{archive_dir}/*')):
        if not os.path.isdir(date_dir):
            continue
        
        for content_dir in glob.glob(f'{date_dir}/*'):
            if not os.path.isdir(content_dir):
                continue
            
            print(f"📦 Exporting: {os.path.basename(content_dir)}")
            data = export_folder(content_dir)
            
            if data:
                all_content.append(data)
    
    # Sort by publish date (newest first)
    all_content.sort(key=lambda x: x.get('publish_date', ''), reverse=True)
    
    # Save to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_content, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Exported {len(all_content)} items to {output_path}")
    return all_content

def export_single(folder_path, output_path=None):
    """Export a single content folder to JSON."""
    if not os.path.exists(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        return
    
    print(f"📦 Exporting: {os.path.basename(folder_path)}")
    data = export_folder(folder_path)
    
    if data:
        if output_path is None:
            output_path = os.path.join(folder_path, 'export.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Exported to {output_path}")
        return data
    else:
        print("❌ Export failed")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 export_to_json.py --all                  # Export all content")
        print("  python3 export_to_json.py <folder_path>          # Export single folder")
        print("  python3 export_to_json.py --all -o output.json   # Specify output file")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        output_file = 'content_export.json'
        if '-o' in sys.argv:
            idx = sys.argv.index('-o')
            if idx + 1 < len(sys.argv):
                output_file = sys.argv[idx + 1]
        export_all(output_file)
    else:
        export_single(sys.argv[1])
