from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def build_manifest(package_dir: Path, source_content_dir: str | None = None, review_status: dict | None = None) -> dict:
    package_dir = Path(package_dir)
    platforms = {}

    xhs_dir = package_dir / "xhs"
    if xhs_dir.exists():
        html_files = []
        index_path = xhs_dir / "index.html"
        if index_path.exists():
            html_files.append(index_path)
        if (xhs_dir / "cards").exists():
            html_files.extend(sorted((xhs_dir / "cards").glob("*.html")))

        png_files = []
        thumbnail_files = []
        if (xhs_dir / "output").exists():
            png_files.extend(sorted((xhs_dir / "output").glob("*.png")))
        if (xhs_dir / "output" / "thumbnails").exists():
            thumbnail_files.extend(sorted((xhs_dir / "output" / "thumbnails").glob("*.png")))
        if (xhs_dir / "cards").exists():
            png_files.extend(sorted((xhs_dir / "cards").glob("*.png")))
        post_path = xhs_dir / "post.md"
        platforms["xhs"] = {
            "post_md": _relative(post_path, package_dir) if post_path.exists() else "",
            "html_count": len(html_files),
            "png_count": len(png_files),
            "thumbnail_count": len(thumbnail_files),
            "html_files": [_relative(path, package_dir) for path in html_files],
            "png_files": [_relative(path, package_dir) for path in png_files],
            "thumbnail_files": [_relative(path, package_dir) for path in thumbnail_files],
        }

    wechat_dir = package_dir / "wechat"
    if wechat_dir.exists():
        html_files = sorted(wechat_dir.glob("*.html"))
        png_files = sorted(wechat_dir.glob("*.png"))
        if (wechat_dir / "output").exists():
            png_files.extend(sorted((wechat_dir / "output").glob("*.png")))
        appendix_path = wechat_dir / "appendix.md"
        platforms["wechat"] = {
            "appendix_md": _relative(appendix_path, package_dir) if appendix_path.exists() else "",
            "html_count": len(html_files),
            "png_count": len(png_files),
            "html_files": [_relative(path, package_dir) for path in html_files],
            "png_files": [_relative(path, package_dir) for path in png_files],
        }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_content_dir": source_content_dir or "",
        "platforms": platforms,
        "review_status": review_status or {},
    }


def write_manifest(package_dir: Path, manifest: dict) -> Path:
    path = Path(package_dir) / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
