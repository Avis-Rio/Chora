"""
小宇宙 (XiaoyuZhou) episode metadata parser.

Provides a resilient, multi-strategy parser for xiaoyuzhoufm.com episode pages.
Falls back through several extraction methods so that minor site changes do not
break the content pipeline.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse


class _MetaExtractor(HTMLParser):
    """Lightweight HTML meta tag / JSON-LD extractor."""

    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.json_ld: list[dict] = []
        self._current_script: str | None = None
        self._script_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k.lower(): v for k, v in attrs if v is not None}
        if tag == "meta":
            name = attr_map.get("name") or attr_map.get("property")
            content = attr_map.get("content")
            if name and content:
                self.meta[name.lower()] = content.strip()
        elif tag == "script":
            self._current_script = attr_map.get("type")
            self._script_buffer = []

    def handle_data(self, data: str) -> None:
        if self._current_script is not None:
            self._script_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._current_script:
            raw = "".join(self._script_buffer)
            if self._current_script.lower() == "application/ld+json":
                try:
                    self.json_ld.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
            self._current_script = None
            self._script_buffer = []


@dataclass(frozen=True)
class EpisodeMetadata:
    """Normalized metadata for a XiaoyuZhou episode."""

    title: str
    channel: str
    upload_date: str
    audio_url: str
    episode_id: str
    description: str
    guests: str
    source_url: str
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "channel": self.channel,
            "upload_date": self.upload_date,
            "audio_url": self.audio_url,
            "episode_id": self.episode_id,
            "guests": self.guests,
            "description": self.description,
            "source_url": self.source_url,
        }


def extract_episode_id(url_or_id: str) -> str | None:
    """Extract episode ID from a XiaoyuZhou URL or return the ID as-is."""
    url_or_id = (url_or_id or "").strip()
    if not url_or_id:
        return None
    if re.fullmatch(r"[a-f0-9]{24}", url_or_id):
        return url_or_id
    parsed = urlparse(url_or_id)
    match = re.search(r"/episode/([a-f0-9]{24})", parsed.path or "")
    if match:
        return match.group(1)
    return None


def _run_curl(url: str, timeout: int = 30) -> str:
    headers = [
        "-H",
        "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "-H",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H",
        "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
    ]
    result = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(timeout)] + headers + [url],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr.strip()}")
    return result.stdout


def fetch_page(url: str, retries: int = 3, backoff: float = 2.0, timeout: int = 30) -> str:
    """Fetch page HTML with retries and exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            html = _run_curl(url, timeout=timeout)
            if len(html.strip()) < 200:
                raise RuntimeError(f"Response too short ({len(html)} chars); possible block/captcha")
            return html
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                sleep_time = backoff * (2**attempt)
                print(
                    f"  ⚠️ Fetch attempt {attempt + 1}/{retries} failed: {exc}. Retrying in {sleep_time}s..."
                )
                time.sleep(sleep_time)
    raise RuntimeError(f"Failed to fetch {url} after {retries} attempts: {last_error}")


def _parse_next_data(html: str) -> dict[str, Any] | None:
    """Parse __NEXT_DATA__ script if present."""
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _extract_from_next_data(next_data: dict[str, Any]) -> dict[str, Any] | None:
    """Pull episode fields from Next.js data structure."""
    if not isinstance(next_data, dict):
        return None
    episode = next_data.get("props", {}).get("pageProps", {}).get("episode")
    if not isinstance(episode, dict):
        return None

    audio_url = (
        episode.get("trial", {}).get("segment", "")
        or episode.get("enclosure", {}).get("url", "")
        or episode.get("associatedMedia", {}).get("contentUrl", "")
        or ""
    )

    podcast = episode.get("podcast", {}) or {}
    pub_date_raw = episode.get("pubDate", "")
    pub_date = pub_date_raw[:10] if pub_date_raw else datetime.now().strftime("%Y-%m-%d")

    return {
        "title": episode.get("title", ""),
        "channel": podcast.get("title", ""),
        "upload_date": pub_date,
        "audio_url": audio_url,
        "description": episode.get("description", ""),
        "_source": "next_data",
    }


def _extract_from_json_ld(json_ld: list[dict]) -> dict[str, Any] | None:
    """Pull episode fields from JSON-LD structured data."""
    for item in json_ld:
        if not isinstance(item, dict):
            continue
        types = {item.get("@type")} if isinstance(item.get("@type"), str) else set(item.get("@type", []))
        if "PodcastEpisode" in types or "AudioObject" in types:
            audio = ""
            if "audio" in item and isinstance(item["audio"], dict):
                audio = item["audio"].get("contentUrl", "") or item["audio"].get("url", "")
            return {
                "title": item.get("name", ""),
                "channel": (
                    item.get("partOfSeries", {}).get("name", "")
                    if isinstance(item.get("partOfSeries"), dict)
                    else ""
                ),
                "upload_date": _normalize_date(item.get("datePublished", "")),
                "audio_url": audio or item.get("contentUrl", ""),
                "description": item.get("description", ""),
                "_source": "json_ld",
            }
    return None


def _extract_from_open_graph(meta: dict[str, str]) -> dict[str, Any] | None:
    """Pull episode fields from OpenGraph / Twitter meta tags."""
    title = meta.get("og:title") or meta.get("twitter:title") or ""
    description = meta.get("og:description") or meta.get("twitter:description") or meta.get("description", "")
    audio_url = meta.get("og:audio") or meta.get("twitter:audio") or ""
    if not title and not description and not audio_url:
        return None
    return {
        "title": title,
        "channel": "",
        "upload_date": datetime.now().strftime("%Y-%m-%d"),
        "audio_url": audio_url,
        "description": description,
        "_source": "open_graph",
    }


def _extract_from_html(html: str) -> dict[str, Any] | None:
    """Last-resort regex-based extraction for title/description/audio."""
    title = ""
    for pattern in [
        r"<h1[^>]*>(.*?)</h1>",
        r"<title>(.*?)</title>",
    ]:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            title = _strip_html(match.group(1)).strip()
            if title:
                break

    description = ""
    match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
    if match:
        description = match.group(1).strip()

    audio_url = ""
    for pattern in [
        r'<audio[^>]+src=["\']([^"\']+)',
        r'<source[^>]+src=["\']([^"\']+)[^>]+type=["\']audio',
        r'["\'](https?://[^"\']+\.m4a[^"\']*)',
        r'["\'](https?://[^"\']+\.mp3[^"\']*)',
    ]:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            audio_url = match.group(1).strip()
            break

    if not title and not audio_url:
        return None
    return {
        "title": title,
        "channel": "",
        "upload_date": datetime.now().strftime("%Y-%m-%d"),
        "audio_url": audio_url,
        "description": description,
        "_source": "html",
    }


def _normalize_date(raw: Any) -> str:
    """Normalize a date string to YYYY-MM-DD."""
    if not raw:
        return datetime.now().strftime("%Y-%m-%d")
    raw_str = str(raw).strip()
    # ISO date
    match = re.match(r"(\d{4}-\d{2}-\d{2})", raw_str)
    if match:
        return match.group(1)
    # ISO datetime
    try:
        dt = datetime.fromisoformat(raw_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    return datetime.now().strftime("%Y-%m-%d")


def _strip_html(raw: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_guests_from_description(description: str) -> str:
    """Extract guest names from a description string."""
    description = description or ""
    # Pattern: 嘉宾：name1、name2 / 嘉宾: name1, name2 / 本期嘉宾：...
    match = re.search(r"(?:嘉宾|本期嘉宾|对谈)[:：]\s*([^\n。！]+)", description)
    if match:
        guests = match.group(1).strip()
        # Clean up separators
        guests = re.sub(r"[、,，;；/\\]+", ", ", guests)
        # Collapse multiple spaces introduced by replacement
        guests = re.sub(r"\s+", " ", guests)
        return guests.strip(" ,")
    return ""


def get_episode_metadata(url_or_id: str) -> EpisodeMetadata:
    """Fetch and normalize metadata for a XiaoyuZhou episode.

    Raises:
        ValueError: if the episode ID cannot be extracted.
        RuntimeError: if the page cannot be fetched or no metadata is found.
    """
    episode_id = extract_episode_id(url_or_id)
    if not episode_id:
        raise ValueError(f"Cannot extract XiaoyuZhou episode ID from {url_or_id!r}")

    url = f"https://www.xiaoyuzhoufm.com/episode/{episode_id}"
    print(f"Fetching metadata from {url}...")

    html = fetch_page(url)
    parser = _MetaExtractor()
    parser.feed(html)

    candidates: list[dict[str, Any]] = []

    next_data = _parse_next_data(html)
    if next_data:
        extracted = _extract_from_next_data(next_data)
        if extracted:
            candidates.append(extracted)

    if parser.json_ld:
        extracted = _extract_from_json_ld(parser.json_ld)
        if extracted:
            candidates.append(extracted)

    og = _extract_from_open_graph(parser.meta)
    if og:
        candidates.append(og)

    html_extracted = _extract_from_html(html)
    if html_extracted:
        candidates.append(html_extracted)

    if not candidates:
        raise RuntimeError(f"Could not extract any metadata for {url}")

    # Merge candidates, preferring earlier (more reliable) sources.
    merged: dict[str, Any] = {}
    for cand in candidates:
        for key, value in cand.items():
            if key.startswith("_"):
                continue
            if value and not merged.get(key):
                merged[key] = value

    title = merged.get("title") or "Unknown Episode"
    channel = merged.get("channel") or "Unknown"
    upload_date = merged.get("upload_date") or datetime.now().strftime("%Y-%m-%d")
    audio_url = merged.get("audio_url") or ""
    description = merged.get("description") or ""
    guests = extract_guests_from_description(description)

    if not audio_url:
        raise RuntimeError(f"Could not extract audio URL for {url}")

    return EpisodeMetadata(
        title=title,
        channel=channel,
        upload_date=upload_date,
        audio_url=audio_url,
        episode_id=episode_id,
        description=description,
        guests=guests,
        source_url=url,
        raw={
            "next_data": next_data,
            "json_ld": parser.json_ld,
            "meta": parser.meta,
            "candidates": candidates,
        },
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 -m xiaoyuzhou_service <url_or_id>")
    meta = get_episode_metadata(sys.argv[1])
    print(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2))
