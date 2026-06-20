from pathlib import Path


def discover_html_outputs(package_dir: Path) -> list[Path]:
    package_dir = Path(package_dir)
    return sorted(package_dir.glob("**/*.html"))


def target_image_path(html_path: Path) -> Path:
    return Path(html_path).with_suffix(".png")


def _generate_thumbnails(output_dir: Path, width: int = 360) -> list[Path]:
    """为每个已导出的 PNG 生成 360px 缩略图，供小屏可读性目检。"""
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


def export_html_to_images(package_dir: Path) -> list[Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required to export distribution images. "
            "Run: python3 -m playwright install chromium"
        ) from exc

    image_paths = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=1)
        for html_path in discover_html_outputs(package_dir):
            output_path = target_image_path(html_path)
            page.goto(html_path.resolve().as_uri())
            card = page.locator(".card")
            card.screenshot(path=str(output_path))
            image_paths.append(output_path)
        browser.close()

    # 360px 缩略图检查
    for html_path in discover_html_outputs(package_dir):
        thumbs = _generate_thumbnails(html_path.parent, width=360)
        image_paths.extend(thumbs)
    return image_paths


def main():
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 -m distribution_pipeline.renderers.html_to_image <package_dir>")
    for path in export_html_to_images(Path(sys.argv[1])):
        print(path)


if __name__ == "__main__":
    main()
