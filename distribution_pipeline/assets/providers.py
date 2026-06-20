from __future__ import annotations

import os
import json
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


def _candidate_id(asset_id: str, provider: str, index: int) -> str:
    return f"{asset_id}-{provider}-{index + 1:02d}"


def default_fetch_json(url: str, headers: dict | None = None) -> dict:
    request = Request(url, headers=headers or {"User-Agent": "ChoraDistribution/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def _compact_candidate(candidate: dict, request: dict, index: int = 0) -> dict:
    asset_id = request.get("asset_id", "image")
    provider = candidate.get("provider") or candidate.get("source_type") or "direct"
    return {
        "candidate_id": candidate.get("candidate_id") or _candidate_id(asset_id, provider, index),
        "asset_id": asset_id,
        "provider": provider,
        "image_url": candidate.get("image_url") or candidate.get("url") or candidate.get("download_url"),
        "source_url": candidate.get("source_url") or candidate.get("page_url") or candidate.get("url"),
        "author": candidate.get("author", ""),
        "author_url": candidate.get("author_url", ""),
        "license_status": candidate.get("license_status", request.get("license_status", "unverified")),
        "width": candidate.get("width"),
        "height": candidate.get("height"),
        "alt": candidate.get("alt") or candidate.get("description") or request.get("query", ""),
        "status": "candidate",
    }


def _pexels_candidates(request: dict, fetch_json, api_key: str, max_candidates: int) -> list[dict]:
    query = quote_plus(request.get("query", ""))
    payload = fetch_json(
        f"https://api.pexels.com/v1/search?query={query}&orientation=landscape&per_page={max_candidates}",
        headers={"Authorization": api_key},
    )
    candidates = []
    for index, photo in enumerate(payload.get("photos", [])[:max_candidates]):
        src = photo.get("src", {})
        candidates.append(
            _compact_candidate(
                {
                    "provider": "pexels",
                    "image_url": src.get("medium") or src.get("large") or src.get("large2x") or src.get("small"),
                    "source_url": photo.get("url"),
                    "author": photo.get("photographer", ""),
                    "author_url": photo.get("photographer_url", ""),
                    "license_status": "pexels-license",
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                    "alt": photo.get("alt", ""),
                },
                request,
                index,
            )
        )
    return [candidate for candidate in candidates if candidate.get("image_url")]


def _unsplash_candidates(request: dict, fetch_json, access_key: str, max_candidates: int) -> list[dict]:
    query = quote_plus(request.get("query", ""))
    payload = fetch_json(
        f"https://api.unsplash.com/search/photos?query={query}&orientation=landscape&per_page={max_candidates}",
        headers={"Authorization": f"Client-ID {access_key}"},
    )
    candidates = []
    for index, photo in enumerate(payload.get("results", [])[:max_candidates]):
        user = photo.get("user", {})
        urls = photo.get("urls", {})
        links = photo.get("links", {})
        candidates.append(
            _compact_candidate(
                {
                    "provider": "unsplash",
                    "image_url": urls.get("regular") or urls.get("full") or urls.get("raw"),
                    "source_url": links.get("html"),
                    "author": user.get("name", ""),
                    "author_url": user.get("links", {}).get("html", ""),
                    "license_status": "unsplash-license",
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                    "alt": photo.get("alt_description") or photo.get("description") or "",
                },
                request,
                index,
            )
        )
    return [candidate for candidate in candidates if candidate.get("image_url")]


def _wallhaven_candidates(request: dict, fetch_json, max_candidates: int) -> list[dict]:
    query = quote_plus(request.get("query", ""))
    payload = fetch_json(
        f"https://wallhaven.cc/api/v1/search?q={query}&sorting=relevance&categories=111&purity=100"
    )
    candidates = []
    for index, item in enumerate(payload.get("data", [])[:max_candidates]):
        candidates.append(
            _compact_candidate(
                {
                    "provider": "wallhaven",
                    "image_url": item.get("path"),
                    "source_url": item.get("url") or item.get("short_url"),
                    "license_status": "unverified",
                    "width": item.get("dimension_x"),
                    "height": item.get("dimension_y"),
                    "alt": request.get("query", ""),
                },
                request,
                index,
            )
        )
    return [candidate for candidate in candidates if candidate.get("image_url")]


def _parse_env_line(line: str) -> tuple[str, str] | None:
    clean = line.strip()
    if not clean or clean.startswith("#"):
        return None
    if clean.startswith("export "):
        clean = clean[len("export ") :].strip()
    if "=" not in clean:
        return None
    key, value = clean.split("=", 1)
    key = key.strip()
    if key not in {"PEXELS_API_KEY", "UNSPLASH_ACCESS_KEY"}:
        return None
    value = value.strip().strip("'\"")
    return key, value


def _dotenv_paths(start: Path | None = None) -> list[Path]:
    current = (start or Path.cwd()).resolve()
    paths = []
    for directory in [current, *current.parents]:
        for name in (".env", ".env.local"):
            path = directory / name
            if path.exists():
                paths.append(path)
    return list(reversed(paths))


def load_image_provider_env(env: dict | None = None) -> dict:
    if env is not None:
        return env

    merged = dict(os.environ)
    shell_keys = set(merged)
    for path in _dotenv_paths():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            parsed = _parse_env_line(line)
            if not parsed:
                continue
            key, value = parsed
            if key not in shell_keys:
                merged[key] = value
    return merged


def discover_image_candidates(
    request: dict,
    *,
    fetch_json=None,
    env: dict | None = None,
    max_candidates: int = 3,
    error_sink: list | None = None,
) -> list[dict]:
    """Return normalized image candidates without requiring network by default."""

    env = load_image_provider_env(env)
    manual = request.get("candidates") or []
    candidates = [
        _compact_candidate(candidate, request, index)
        for index, candidate in enumerate(manual[:max_candidates])
    ]

    selected_url = request.get("selected_url") or request.get("source_url") or request.get("image_url")
    if selected_url and not candidates:
        candidates.append(
            _compact_candidate(
                {
                    "provider": request.get("provider", "direct"),
                    "image_url": selected_url,
                    "source_url": request.get("source_url") or selected_url,
                    "author": request.get("author", ""),
                    "license_status": request.get("license_status", "unverified"),
                },
                request,
            )
        )

    if not fetch_json:
        return [candidate for candidate in candidates if candidate.get("image_url")]

    provider_calls = []
    if env.get("PEXELS_API_KEY"):
        provider_calls.append(
            ("pexels", lambda: _pexels_candidates(request, fetch_json, env["PEXELS_API_KEY"], max_candidates))
        )
    if env.get("UNSPLASH_ACCESS_KEY"):
        provider_calls.append(
            (
                "unsplash",
                lambda: _unsplash_candidates(request, fetch_json, env["UNSPLASH_ACCESS_KEY"], max_candidates),
            )
        )
    if "wallhaven" in request.get("providers", []):
        provider_calls.append(("wallhaven", lambda: _wallhaven_candidates(request, fetch_json, max_candidates)))

    for provider, provider_call in provider_calls:
        try:
            candidates.extend(provider_call())
        except Exception as exc:  # pragma: no cover - exact network errors vary by platform
            if error_sink is not None:
                error_sink.append({"provider": provider, "error": str(exc)})

    seen = set()
    unique = []
    for candidate in candidates:
        image_url = candidate.get("image_url")
        if not image_url or image_url in seen:
            continue
        seen.add(image_url)
        unique.append(candidate)
        if len(unique) >= max_candidates:
            break
    return unique
