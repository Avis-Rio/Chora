"""
content_archive 自动清理工具。

策略：
- 默认删除超过 30 天的音频文件（audio.m4a / audio.mp3），释放磁盘空间。
- 保留核心文件：metadata.md、transcript.md、rewritten.md、cover.*、distribution/。
- 支持 --dry-run 预览、--days 自定义天数、--remove-covers 同时清理旧封面。

用法：
    python3 utils/archive_cleanup.py
    python3 utils/archive_cleanup.py --days 7 --dry-run
    python3 utils/archive_cleanup.py --remove-covers --days 90
"""

import os
import sys
import argparse
from datetime import datetime, timedelta


def parse_args():
    parser = argparse.ArgumentParser(description="清理 content_archive 中的过期大文件")
    parser.add_argument(
        "--archive-dir",
        default="./content_archive",
        help="归档目录路径（默认：./content_archive）",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="删除超过 N 天的文件（默认：30）",
    )
    parser.add_argument(
        "--remove-covers",
        action="store_true",
        help="同时删除超过天数的封面图（默认保留）",
    )
    parser.add_argument(
        "--remove-empty-dirs",
        action="store_true",
        help="删除清理后变为空的子目录",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览，不实际删除",
    )
    return parser.parse_args()


def should_remove_file(filename, remove_covers):
    """判断文件是否属于可清理的大文件类型。"""
    lower = filename.lower()
    if lower in ("audio.m4a", "audio.mp3"):
        return True
    if lower.startswith("temp_chunk_") and lower.endswith((".mp3", ".m4a")):
        return True
    if remove_covers and lower.startswith("cover.") and lower.split(".")[-1] in (
        "jpg", "jpeg", "png", "webp", "gif"
    ):
        return True
    return False


def find_removable_files(archive_dir, days, remove_covers):
    cutoff = datetime.now() - timedelta(days=days)
    removable = []

    for root, dirs, files in os.walk(archive_dir):
        # 不进入 distribution 子目录
        dirs[:] = [d for d in dirs if d != "distribution"]

        for filename in files:
            if not should_remove_file(filename, remove_covers):
                continue
            path = os.path.join(root, filename)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
            except OSError:
                continue
            if mtime < cutoff:
                removable.append((path, os.path.getsize(path), mtime))

    return removable


def remove_empty_dirs(archive_dir, dry_run):
    removed = 0
    for root, dirs, files in os.walk(archive_dir, topdown=False):
        # 跳过根目录本身
        if root == archive_dir:
            continue
        # 如果目录为空则删除
        try:
            if not os.listdir(root):
                if not dry_run:
                    os.rmdir(root)
                removed += 1
        except OSError:
            continue
    return removed


def main():
    args = parse_args()
    archive_dir = os.path.abspath(args.archive_dir)

    if not os.path.exists(archive_dir):
        print(f"❌ 归档目录不存在: {archive_dir}")
        sys.exit(1)

    removable = find_removable_files(archive_dir, args.days, args.remove_covers)
    total_size = sum(size for _, size, _ in removable)

    if not removable:
        print(f"✅ 未发现超过 {args.days} 天的可清理文件。")
        return

    mode = "[预览，不删除]" if args.dry_run else "[即将删除]"
    print(f"{mode} 发现 {len(removable)} 个可清理文件，预计释放 {total_size / (1024**2):.1f} MB")

    for path, size, mtime in sorted(removable):
        rel = os.path.relpath(path, archive_dir)
        print(f"  - {rel} ({size / (1024**2):.1f} MB, {mtime.date()})")
        if not args.dry_run:
            try:
                os.remove(path)
            except OSError as e:
                print(f"    ❌ 删除失败: {e}")

    if args.remove_empty_dirs:
        empty_removed = remove_empty_dirs(archive_dir, args.dry_run)
        if empty_removed:
            print(f"{'[预览]' if args.dry_run else ''} 清理空目录: {empty_removed} 个")

    if not args.dry_run:
        print(f"✅ 已清理，释放 {total_size / (1024**2):.1f} MB")


if __name__ == "__main__":
    main()
