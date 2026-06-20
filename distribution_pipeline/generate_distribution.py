import argparse
import re
from pathlib import Path

from distribution_pipeline.extractors.package_builder import build_content_package
from distribution_pipeline.renderers.guizang.exporter import export_guizang_images
from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_wechat_package
from distribution_pipeline.renderers.guizang.guizang_renderer import render_guizang_xhs_package
from distribution_pipeline.renderers.guizang.guizang_renderer import resolve_guizang_mode
from distribution_pipeline.renderers.guizang.validator import run_guizang_validator
from distribution_pipeline.renderers.html_to_image import export_html_to_images
from distribution_pipeline.renderers.manifest import build_manifest, write_manifest
from distribution_pipeline.renderers.wechat_renderer import render_wechat_package
from distribution_pipeline.renderers.xhs_renderer import render_xhs_package
from distribution_pipeline.reviewers.repetition import review_repetition


GUIZANG_VALIDATOR_NO_EXPORT_REASON = "Guizang validator skipped because image export is disabled."


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fa5-]+", "-", text).strip("-")
    return slug[:80] or "distribution-package"


def run(
    content_dir: Path,
    output_root: Path = Path("distribution"),
    platform: str = "xhs",
    style_id: str = "chora-editorial",
    max_cards: int | None = None,
    export_images: bool = True,
    renderer: str = "basic",
    guizang_mode: str = "auto",
    guizang_theme: str = "auto",
    image_asset_mode: str = "plan",
) -> Path:
    content_dir = Path(content_dir)
    output_root = Path(output_root)
    package_dir = output_root / _slugify(content_dir.name)

    if renderer not in ("basic", "guizang"):
        raise ValueError(f"Unknown renderer: {renderer}")
    if platform not in ("all", "xhs", "wechat"):
        raise ValueError(f"Unknown platform: {platform}")

    package = build_content_package(content_dir, package_dir)

    if renderer == "guizang":
        xhs_guizang_mode = resolve_guizang_mode(package, guizang_mode, target="xhs")
        wechat_guizang_mode = resolve_guizang_mode(package, guizang_mode, target="wechat")
        if platform in ("all", "xhs"):
            render_guizang_xhs_package(
                package,
                package_dir,
                max_cards=max_cards,
                mode=xhs_guizang_mode,
                theme=guizang_theme,
                image_asset_mode=image_asset_mode,
            )
        if platform in ("all", "wechat"):
            render_guizang_wechat_package(
                package,
                package_dir,
                mode=wechat_guizang_mode,
                theme=guizang_theme,
                image_asset_mode=image_asset_mode,
            )
        if export_images:
            export_guizang_images(package_dir)
            guizang_review = {}
            if platform in ("all", "xhs"):
                guizang_review["xhs"] = run_guizang_validator(package_dir / "xhs", mode=xhs_guizang_mode)
            if platform in ("all", "wechat"):
                guizang_review["wechat"] = run_guizang_validator(package_dir / "wechat", mode=wechat_guizang_mode)
        else:
            skipped_review = {
                "status": "skipped",
                "reason": GUIZANG_VALIDATOR_NO_EXPORT_REASON,
            }
            guizang_review = {}
            if platform in ("all", "xhs"):
                guizang_review["xhs"] = skipped_review
            if platform in ("all", "wechat"):
                guizang_review["wechat"] = skipped_review
        review_status = {
            "repetition": review_repetition(package.get("visual_briefs", [])),
            "guizang": guizang_review,
        }
        manifest = build_manifest(
            package_dir,
            source_content_dir=str(content_dir),
            review_status=review_status,
        )
        write_manifest(package_dir, manifest)
        return package_dir

    if max_cards is None:
        max_cards = 8

    if platform in ("all", "xhs"):
        render_xhs_package(package, package_dir, style_id=style_id, max_cards=max_cards)
    if platform in ("all", "wechat"):
        render_wechat_package(package, package_dir, style_id=style_id)

    if export_images:
        export_html_to_images(package_dir)

    review_status = {
        "repetition": review_repetition(package.get("visual_briefs", [])),
    }
    manifest = build_manifest(
        package_dir,
        source_content_dir=str(content_dir),
        review_status=review_status,
    )
    write_manifest(package_dir, manifest)
    return package_dir


def main():
    parser = argparse.ArgumentParser(description="生成 Chora 分发素材包")
    parser.add_argument("content_folder", type=Path)
    parser.add_argument(
        "--platform",
        default="xhs",
        choices=["all", "xhs", "wechat"],
        help="輸出平台；默認僅 xhs（小紅書），wechat 為按需交付物，需顯式指定。",
    )
    parser.add_argument("--style", dest="style_id", default="chora-editorial")
    parser.add_argument("--cards", dest="max_cards", type=int, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("distribution"))
    parser.add_argument("--no-export-images", action="store_true")
    parser.add_argument("--renderer", default="basic", choices=["basic", "guizang"])
    parser.add_argument("--guizang-mode", default="auto", choices=["auto", "llm", "editorial", "swiss"], help="Guizang mode：auto 啟發式；llm 外部 LLM 自定（需 CHORA_DISTRIBUTION_MODE_LLM_URL/_KEY）；editorial/swiss 強制指定。")
    parser.add_argument("--guizang-theme", default="auto")
    parser.add_argument(
        "--image-assets",
        default="plan",
        choices=["plan", "candidates", "download"],
        help="Guizang 图像资产处理模式：plan 仅写搜索计划，candidates 仅拉候选，download 下载首选候选。",
    )
    args = parser.parse_args()

    package_dir = run(
        content_dir=args.content_folder,
        output_root=args.output_root,
        platform=args.platform,
        style_id=args.style_id,
        max_cards=args.max_cards,
        export_images=not args.no_export_images,
        renderer=args.renderer,
        guizang_mode=args.guizang_mode,
        guizang_theme=args.guizang_theme,
        image_asset_mode=args.image_assets,
    )
    print(f"Distribution package generated: {package_dir}")


if __name__ == "__main__":
    main()
