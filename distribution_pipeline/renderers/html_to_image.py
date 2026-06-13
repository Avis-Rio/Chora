from pathlib import Path


def discover_html_outputs(package_dir: Path) -> list[Path]:
    package_dir = Path(package_dir)
    return sorted(package_dir.glob("**/*.html"))


def target_image_path(html_path: Path) -> Path:
    return Path(html_path).with_suffix(".png")


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
    return image_paths


def main():
    import sys

    if len(sys.argv) < 2:
        raise SystemExit("Usage: python3 -m distribution_pipeline.renderers.html_to_image <package_dir>")
    for path in export_html_to_images(Path(sys.argv[1])):
        print(path)


if __name__ == "__main__":
    main()
