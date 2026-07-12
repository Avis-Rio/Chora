#!/usr/bin/env python3
"""
Generate frontend data from content_export.json.
Copies data to frontend/public/data for static hosting.
"""

import os
import json
import shutil

def _clean_tag(tag):
    """Strip markdown backticks and surrounding whitespace from a tag.

    Rewritten content sometimes emits tags wrapped in inline code (e.g.
    `` `Deep Dive` ``) when the LLM copies them directly from heading slugs.
    We unwrap them so the tag cloud renders cleanly and summary.json
    duplicates do not pollute frontend filters.
    """
    if not isinstance(tag, str):
        return ''
    return tag.strip().strip('`').strip()


def _dedupe_tags(tags):
    """Deduplicate tags after cleaning (case-insensitive, preserve order)."""
    seen = set()
    out = []
    for raw in tags or []:
        cleaned = _clean_tag(raw)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def generate_frontend_data(
    export_path='content_export.json',
    output_dirs=('frontend/public/data', 'frontend/data')
):
    """Convert export data to frontend-friendly format.

    Writes to BOTH ``frontend/public/data`` (Vercel static origin) and
    ``frontend/data`` (the fallback path ``app.js`` hits when ``/api/content``
    fails). Keeping these two files in sync prevents the fallback returning
    stale 9-row data while the live API serves 44.
    """

    if not os.path.exists(export_path):
        print(f"❌ Export file not found: {export_path}")
        return

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
            'tags': _dedupe_tags(item.get('tags', [])),
            'excerpt': excerpt,
            'rewritten': item.get('rewritten', ''),
            'quotes': [q.lstrip('> \t　') for q in item.get('quotes', [])],
            'guests': item.get('guests', ''),
            'url': item.get('source_url', '') or item.get('url', ''),
            'score': item.get('score', 0)
        }
        
        frontend_data.append(frontend_item)
    
    # Sort by publish date (newest first)
    frontend_data.sort(key=lambda x: x.get('publish_date', ''), reverse=True)
    
    # Write to each output directory (public for Vercel, root for fallback)
    for output_dir in output_dirs:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'content.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(frontend_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Generated {len(frontend_data)} items to {output_path}")

    # Also generate a summary for stats (same cleaned tag universe, preserves order)
    summary = {
        'total': len(frontend_data),
        'youtube': len([i for i in frontend_data if i['platform'] == 'YouTube']),
        'podcast': len([i for i in frontend_data if i['platform'] == '小宇宙']),
        'tags': _dedupe_tags([tag for item in frontend_data for tag in item.get('tags', [])])
    }

    for output_dir in output_dirs:
        summary_path = os.path.join(output_dir, 'summary.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"✅ Generated summary to {summary_path}")

if __name__ == "__main__":
    generate_frontend_data()
