#!/usr/bin/env python3
"""
Generate frontend data from content_export.json.
Copies data to frontend/public/data for static hosting.
"""

import os
import json
import shutil

def generate_frontend_data(
    export_path='content_export.json',
    output_dir='frontend/public/data'
):
    """Convert export data to frontend-friendly format."""
    
    if not os.path.exists(export_path):
        print(f"❌ Export file not found: {export_path}")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    with open(export_path, 'r', encoding='utf-8') as f:
        items = json.load(f)
    
    # Transform data for frontend
    frontend_data = []
    
    for item in items:
        # Map cover path to public URL
        cover_url = None
        if item.get('cover_path'):
            filename = os.path.basename(item['cover_path'])
            # Use the synced cover filename
            folder = os.path.basename(os.path.dirname(item['cover_path']))
            safe_name = folder.replace(' ', '_')[:50]
            ext = filename.split('.')[-1] if '.' in filename else 'jpg'
            cover_url = f"/covers/{safe_name}.{ext}"
        
        # Extract excerpt from rewritten content
        excerpt = ''
        if item.get('rewritten'):
            # Get first 150 chars of content as excerpt
            content = item['rewritten']
            # Skip any headers
            lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
            if lines:
                excerpt = lines[0][:200] + '...' if len(lines[0]) > 200 else lines[0]
        
        frontend_item = {
            'id': item.get('id', ''),
            'title': item.get('title', ''),
            'platform': item.get('platform', '').replace('youtube', 'YouTube').replace('xiaoyuzhou', '小宇宙'),
            'channel': item.get('channel', ''),
            'publish_date': item.get('publish_date', ''),
            'reading_time': item.get('reading_time', 10),
            'cover_url': cover_url,
            'tags': item.get('tags', []),
            'excerpt': excerpt,
            'rewritten': item.get('rewritten', ''),
            'quotes': item.get('quotes', []),
            'guests': item.get('guests', ''),
            'url': item.get('source_url', '') or item.get('url', ''),
            'score': item.get('score', 0)
        }
        
        frontend_data.append(frontend_item)
    
    # Sort by publish date (newest first)
    frontend_data.sort(key=lambda x: x.get('publish_date', ''), reverse=True)
    
    # Write to frontend data directory
    output_path = os.path.join(output_dir, 'content.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(frontend_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Generated {len(frontend_data)} items to {output_path}")
    
    # Also generate a summary for stats
    summary = {
        'total': len(frontend_data),
        'youtube': len([i for i in frontend_data if i['platform'] == 'YouTube']),
        'podcast': len([i for i in frontend_data if i['platform'] == '小宇宙']),
        'tags': list(set(tag for item in frontend_data for tag in item.get('tags', [])))
    }
    
    summary_path = os.path.join(output_dir, 'summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Generated summary to {summary_path}")

if __name__ == "__main__":
    generate_frontend_data()
