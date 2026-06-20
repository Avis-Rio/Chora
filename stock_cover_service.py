"""
Stock photo fallback for Chora cover generation.

Supports Pexels and Unsplash as fallbacks when Gemini image generation fails.
Downloads a relevant image, optionally resizes it to 16:9, and saves to the
requested output path.

Required environment variables:
- PEXELS_API_KEY
- UNSPLASH_ACCESS_KEY
"""

from __future__ import annotations

import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Iterable

import requests


PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()

# Ensure .env is loaded when running outside the main entry point
try:
    from dotenv import load_dotenv

    load_dotenv()
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", PEXELS_API_KEY).strip()
    UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", UNSPLASH_ACCESS_KEY).strip()
except ImportError:
    pass


def _is_placeholder(value: str) -> bool:
    return not value or "your_" in value.lower() or value.startswith("***")


def _build_search_query(title: str, description: str | None = None, max_terms: int = 6) -> str:
    """Build an English-friendly stock-photo query from Chinese/English title."""
    text = f"{title or ''} {description or ''}".strip()
    # Remove episode numbers like EP01, Vol.12, 午后偏见044
    text = re.sub(r"\b(?:Vol|Ep|No|Part)\.?\s*\d+\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[一-龥]+\d+", "", text)
    # Remove common podcast prefixes/punctuation
    text = re.sub(r"[｜|︱│丨—–\-:：#（）()【】\[\]]+", " ", text)
    # Remove pure Chinese stopwords and generic punctuation
    stopwords = {"的", "了", "与", "和", "是", "在", "有", "我", "你", "谈", "及", "等"}
    tokens = []
    for raw in re.split(r"\s+", text):
        t = raw.strip()
        if not t or t in stopwords:
            continue
        tokens.append(t)
    query = " ".join(tokens[:max_terms])
    return query.strip()


def _download_image(url: str, output_path: Path, timeout: int = 30) -> bool:
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
        return True
    except Exception as exc:
        print(f"   ⚠️ Download failed: {exc}")
        return False


def _resize_to_16x9(image_path: Path) -> bool:
    """Crop/resize an image to approximately 16:9 using Pillow."""
    try:
        from PIL import Image
    except ImportError:
        return True  # No Pillow; leave image as-is

    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            target_ratio = 16 / 9
            current_ratio = width / height

            if current_ratio > target_ratio:
                # Image is too wide; crop width
                new_width = int(height * target_ratio)
                left = (width - new_width) // 2
                img = img.crop((left, 0, left + new_width, height))
            elif current_ratio < target_ratio:
                # Image is too tall; crop height
                new_height = int(width / target_ratio)
                top = (height - new_height) // 2
                img = img.crop((0, top, width, top + new_height))

            # Downscale if huge to keep file size reasonable
            if img.width > 1920:
                img = img.resize((1920, 1080), Image.Resampling.LANCZOS)

            img.save(image_path, "JPEG", quality=90)
        return True
    except Exception as exc:
        print(f"   ⚠️ Resize failed: {exc}")
        return False


def search_pexels(query: str, per_page: int = 10) -> list[str]:
    """Return list of image URLs from Pexels."""
    if _is_placeholder(PEXELS_API_KEY):
        return []

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        photos = data.get("photos", [])
        return [p["src"]["large2x"] for p in photos if "src" in p and "large2x" in p["src"]]
    except Exception as exc:
        print(f"   ⚠️ Pexels search failed: {exc}")
        return []


def search_unsplash(query: str, per_page: int = 10) -> list[str]:
    """Return list of image URLs from Unsplash."""
    if _is_placeholder(UNSPLASH_ACCESS_KEY):
        return []

    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        return [r["urls"]["regular"] for r in results if "urls" in r and "regular" in r["urls"]]
    except Exception as exc:
        print(f"   ⚠️ Unsplash search failed: {exc}")
        return []


def download_stock_cover(
    title: str,
    output_path: str | Path,
    description: str | None = None,
    providers: Iterable[str] = ("pexels", "unsplash"),
    resize: bool = True,
) -> bool:
    """Try to download a relevant stock photo as a cover fallback.

    Args:
        title: Episode/content title.
        output_path: Where to save the image.
        description: Optional description to enrich the search query.
        providers: Order of providers to try.
        resize: Whether to crop/resize to 16:9 after download.

    Returns:
        True if an image was successfully downloaded.
    """
    output_path = Path(output_path)
    query = _build_search_query(title, description)
    if not query:
        print("   ⚠️ Could not build a stock photo search query.")
        return False

    print(f"   🔍 Stock photo query: {query}")

    for provider in providers:
        if provider == "pexels":
            urls = search_pexels(query)
        elif provider == "unsplash":
            urls = search_unsplash(query)
        else:
            continue

        for idx, image_url in enumerate(urls):
            print(f"   📥 Trying {provider} image {idx + 1}/{len(urls)}...")
            if _download_image(image_url, output_path):
                if resize:
                    _resize_to_16x9(output_path)
                size_kb = output_path.stat().st_size / 1024
                print(f"   ✅ Stock cover saved: {output_path} ({size_kb:.1f} KB)")
                return True
            time.sleep(0.2)

    print("   ❌ No suitable stock photo found.")
    return False
