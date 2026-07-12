from __future__ import annotations

import re
import struct
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

IMAGE_SIGNATURES = {
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"RIFF": ".webp",
}


def _default_fetch_bytes(url: str, headers: dict | None = None):
    request = Request(url, headers=headers or {"User-Agent": "ChoraDistribution/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read(), response.headers.get("Content-Type", "")


def _safe_slug(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fa5-]+", "-", str(text or "")).strip("-").lower()
    return slug[:80] or "image"


def _extension_from_bytes(data: bytes, fallback_url: str = "") -> str:
    for signature, extension in IMAGE_SIGNATURES.items():
        if data.startswith(signature):
            return extension
    suffix = Path(urlparse(fallback_url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    return ".jpg"


def _png_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24:
        return None
    return struct.unpack(">II", data[16:24])


def _jpeg_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"\xff\xd8"):
        return None
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            return None
        length = struct.unpack(">H", data[offset : offset + 2])[0]
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if offset + 7 > len(data):
                return None
            height = struct.unpack(">H", data[offset + 3 : offset + 5])[0]
            width = struct.unpack(">H", data[offset + 5 : offset + 7])[0]
            return width, height
        offset += length
    return None


def _webp_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 30 or not data.startswith(b"RIFF") or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if chunk == b"VP8 " and len(data) >= 30:
        width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return width, height
    if chunk == b"VP8L" and len(data) >= 25:
        bits = int.from_bytes(data[21:25], "little")
        width = 1 + (bits & 0x3FFF)
        height = 1 + ((bits >> 14) & 0x3FFF)
        return width, height
    return None


def inspect_image_bytes(data: bytes) -> dict:
    size = _png_size(data) or _jpeg_size(data) or _webp_size(data)
    return {
        "byte_size": len(data),
        "width": size[0] if size else None,
        "height": size[1] if size else None,
    }


def download_candidate(
    request: dict,
    candidate: dict,
    images_dir: Path,
    *,
    fetch_bytes=None,
    min_width: int = 640,
    min_height: int = 480,
) -> dict:
    fetch_bytes = fetch_bytes or _default_fetch_bytes
    images_dir = Path(images_dir)
    image_url = candidate.get("image_url")
    if not image_url:
        return {**candidate, "status": "rejected", "reason": "missing image_url"}

    try:
        fetched = fetch_bytes(image_url)
        if isinstance(fetched, tuple):
            data = fetched[0]
            content_type = fetched[1] if len(fetched) > 1 else ""
        else:
            data = fetched
            content_type = ""
    except Exception as exc:  # pragma: no cover - exact network errors vary by platform
        return {**candidate, "status": "download_failed", "reason": str(exc)}

    if not data:
        return {**candidate, "status": "rejected", "reason": "empty response"}

    inspection = inspect_image_bytes(data)
    width = inspection.get("width") or candidate.get("width")
    height = inspection.get("height") or candidate.get("height")
    if width and height and (int(width) < min_width or int(height) < min_height):
        return {
            **candidate,
            **inspection,
            "status": "rejected",
            "reason": f"image too small: {width}x{height}",
        }

    extension = _extension_from_bytes(data, image_url)
    filename = f"{_safe_slug(request.get('asset_id'))}{extension}"
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / filename
    target.write_bytes(data)

    return {
        **candidate,
        **inspection,
        "status": "available",
        "filename": filename,
        "render_path": f"assets/images/{filename}",
        "content_type": content_type,
        "width": width,
        "height": height,
        "target_pages": request.get("target_pages", []),
        "target_insight_index": request.get("target_insight_index"),
        "role": request.get("role", ""),
        "caption": candidate.get("alt") or request.get("query", ""),
        "object_position": candidate.get("object_position", "center 50%"),
        "preferred_recipe": request.get("preferred_recipe", ""),
    }
