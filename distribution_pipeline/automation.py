from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import traceback

from distribution_pipeline.generate_distribution import run as run_distribution


FALSE_VALUES = {"0", "false", "no", "off", "否", "不"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in FALSE_VALUES


def _env_int(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _append_error(content_dir: Path, context: str, exc: Exception) -> None:
    log_path = content_dir / "distribution_errors.log"
    timestamp = datetime.now().isoformat(timespec="seconds")
    message = "\n".join(
        [
            f"[{timestamp}] Guizang distribution failed",
            f"context: {context or 'unknown'}",
            f"error: {exc}",
            traceback.format_exc(),
            "",
        ]
    )
    try:
        log_path.write_text(
            (log_path.read_text(encoding="utf-8") if log_path.exists() else "") + message,
            encoding="utf-8",
        )
    except Exception:
        pass


def generate_distribution_after_rewrite(
    content_dir: str | Path,
    *,
    context: str = "",
    export_images: bool | None = None,
    image_asset_mode: str | None = None,
    output_root: str | Path | None = None,
    platform: str | None = None,
    max_cards: int | None = None,
) -> Path | None:
    """在 rewrite 成功后生成 Guizang 小红书分发包；失败时记录并继续主流程。"""
    if not _env_bool("CHORA_DISTRIBUTION_AUTO", True):
        print("Guizang distribution auto step disabled by CHORA_DISTRIBUTION_AUTO.")
        return None

    content_path = Path(content_dir)
    if not (content_path / "metadata.md").exists() or not (content_path / "rewritten.md").exists():
        print("Guizang distribution skipped: metadata.md or rewritten.md missing.")
        return None

    resolved_export_images = (
        _env_bool("CHORA_DISTRIBUTION_EXPORT_IMAGES", True)
        if export_images is None
        else export_images
    )
    resolved_image_assets = image_asset_mode or os.environ.get("CHORA_DISTRIBUTION_IMAGE_ASSETS", "plan")
    resolved_output_root = Path(output_root or os.environ.get("CHORA_DISTRIBUTION_OUTPUT_ROOT", "distribution"))
    resolved_platform = platform or os.environ.get("CHORA_DISTRIBUTION_PLATFORM", "xhs")
    resolved_max_cards = max_cards if max_cards is not None else _env_int("CHORA_DISTRIBUTION_MAX_CARDS")

    print("\n[分发] Generating Guizang XHS package...")
    try:
        package_dir = run_distribution(
            content_dir=content_path,
            output_root=resolved_output_root,
            platform=resolved_platform,
            max_cards=resolved_max_cards,
            export_images=resolved_export_images,
            renderer="guizang",
            guizang_mode="auto",
            guizang_theme=os.environ.get("CHORA_DISTRIBUTION_THEME", "auto"),
            image_asset_mode=resolved_image_assets,
        )
    except Exception as exc:
        _append_error(content_path, context, exc)
        print(f"⚠️ Guizang distribution failed; logged to {content_path / 'distribution_errors.log'}")
        return None

    print(f"✅ Guizang distribution package: {package_dir}")
    return package_dir

