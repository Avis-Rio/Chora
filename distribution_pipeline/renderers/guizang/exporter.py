import os
import subprocess
from pathlib import Path

DEPENDENCY_MESSAGE = (
    "Guizang image export requires Node.js and Playwright. " "Playwright browser binaries are also required."
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
# Playwright 默認瀏覽器緩存（macOS / Linux 兩套）；無則 Playwright 自己 fall back
_DEFAULT_PLAYWRIGHT_BROWSERS = (
    Path.home() / "Library" / "Caches" / "ms-playwright",  # macOS
    Path.home() / ".cache" / "ms-playwright",  # Linux
)
PROJECT_PLAYWRIGHT_BROWSERS = PROJECT_ROOT / ".ms-playwright"


def _resolve_default_playwright_browsers() -> Path | None:
    """優先已存在的 ms-playwright 目錄（用戶緩存 > 項目緩存）。"""
    for candidate in (*_DEFAULT_PLAYWRIGHT_BROWSERS, PROJECT_PLAYWRIGHT_BROWSERS):
        if candidate.is_dir():
            return candidate
    return PROJECT_PLAYWRIGHT_BROWSERS


def discover_guizang_render_scripts(package_dir: Path) -> list[Path]:
    package_dir = Path(package_dir)
    return sorted(package_dir.glob("*/render.cjs"))


def _is_missing_playwright(text: str) -> bool:
    return (
        "ERR_MODULE_NOT_FOUND" in text
        or "Cannot find package 'playwright'" in text
        or "Cannot find module 'playwright'" in text
    )


def _node_env() -> dict[str, str]:
    env = os.environ.copy()
    paths = [str(path / "node_modules") for path in [PROJECT_ROOT, *PROJECT_ROOT.parents]]
    if env.get("NODE_PATH"):
        paths.append(env["NODE_PATH"])
    env["NODE_PATH"] = os.pathsep.join(paths)
    if "PLAYWRIGHT_BROWSERS_PATH" not in env:
        default_dir = _resolve_default_playwright_browsers()
        if default_dir is not None:
            env["PLAYWRIGHT_BROWSERS_PATH"] = str(default_dir)
    return env


def _generate_thumbnails(output_dir: Path, width: int = 360) -> list[Path]:
    """为每个已导出的 PNG 生成小尺寸缩略图，供 360px 可读性目检。"""
    try:
        from PIL import Image
    except ImportError:
        return []

    output_dir = Path(output_dir)
    thumb_dir = output_dir / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumbs: list[Path] = []

    for png_path in sorted(output_dir.glob("*.png")):
        try:
            with Image.open(png_path) as img:
                orig_width, orig_height = img.size
                height = int(orig_height * width / orig_width)
                thumb = img.resize((width, height), Image.Resampling.LANCZOS)
                thumb_path = thumb_dir / f"{png_path.stem}_thumb{width}.png"
                thumb.save(thumb_path, "PNG")
                thumbs.append(thumb_path)
        except Exception as exc:
            print(f"  ⚠️ 缩略图生成失败 {png_path.name}: {exc}")
    return thumbs


def export_guizang_images(package_dir: Path) -> list[Path]:
    package_dir = Path(package_dir)
    scripts = discover_guizang_render_scripts(package_dir)
    image_paths: list[Path] = []

    for script in scripts:
        print(f"Guizang image export: running {script}")
        try:
            subprocess.run(
                ["node", "render.cjs"],
                cwd=script.parent,
                check=True,
                text=True,
                env=_node_env(),
                timeout=180,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(DEPENDENCY_MESSAGE) from exc
        except subprocess.CalledProcessError as exc:
            details = "\n".join(part for part in [exc.output, exc.stderr] if part)
            if _is_missing_playwright(details):
                raise RuntimeError(DEPENDENCY_MESSAGE) from exc
            suffix = f"\n{details}" if details else "\nSee render output above."
            raise RuntimeError(f"Guizang image export failed for {script}:{suffix}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Guizang image export timed out for {script}") from exc
        image_paths.extend(sorted((script.parent / "output").glob("*.png")))
        # 360px 缩略图检查
        thumbs = _generate_thumbnails(script.parent / "output", width=360)
        if thumbs:
            print(f"  Generated {len(thumbs)} 360px thumbnails for manual readability check")
        image_paths.extend(thumbs)

    return image_paths
