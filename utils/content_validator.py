#!/usr/bin/env python3
"""
内容完整性验证工具
用于检查 content_archive 中所有内容的文件完整性
支持飞书同步前的预检查
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 必需文件列表
REQUIRED_FILES = {
    "cover": ["cover.jpg", "cover.png", "cover.webp"],
    "metadata": "metadata.md",
    "transcript": "transcript.md",
    "rewritten": "rewritten.md",
}

# 可选文件
OPTIONAL_FILES = ["audio.m4a", "audio.mp3", "cover_optimized.png"]


def check_directory(dir_path: str, verbose: bool = False) -> dict:
    """
    检查单个内容目录的完整性

    返回: {
        'valid': bool,
        'missing': list,
        'present': list,
        'size_info': dict
    }
    """
    dir_path = Path(dir_path)
    result = {"valid": True, "missing": [], "present": [], "size_info": {}}

    # 检查封面（任意一种格式即可）
    cover_found = False
    for cover_file in REQUIRED_FILES["cover"]:
        cover_path = dir_path / cover_file
        if cover_path.exists():
            cover_found = True
            result["present"].append(cover_file)
            result["size_info"][cover_file] = cover_path.stat().st_size
            break

    if not cover_found:
        result["valid"] = False
        result["missing"].append("cover (cover.jpg/png/webp)")

    # 检查其他必需文件
    for key in ["metadata", "transcript", "rewritten"]:
        file_name = REQUIRED_FILES[key]
        file_path = dir_path / file_name
        if file_path.exists():
            result["present"].append(file_name)
            result["size_info"][file_name] = file_path.stat().st_size
        else:
            result["valid"] = False
            result["missing"].append(file_name)

    return result


def scan_content_archive(
    archive_root: str = "content_archive",
    days: int = 30,
    only_invalid: bool = False,
    fix_mode: bool = False,
    verbose: bool = False,
) -> dict:
    """
    扫描整个内容存档目录

    Args:
        archive_root: 内容存档根目录
        days: 检查最近 N 天的内容（0 表示全部）
        only_invalid: 只返回无效条目
        fix_mode: 修复模式 - 生成缺失的 rewritten.md
        verbose: 详细输出

    Returns: {
        'total_dirs': int,
        'valid_count': int,
        'invalid_count': int,
        'invalid_entries': list,
        'fix_commands': list
    }
    """
    archive_root = Path(archive_root)
    stats = {"total_dirs": 0, "valid_count": 0, "invalid_count": 0, "invalid_entries": [], "fix_commands": []}

    # 计算日期范围
    if days > 0:
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")
    else:
        cutoff_str = None

    # 遍历所有日期目录
    for date_dir in sorted(archive_root.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue

        # 日期过滤
        if cutoff_str and date_dir.name < cutoff_str:
            continue

        # 遍历该日期下的所有内容目录
        for content_dir in date_dir.iterdir():
            if not content_dir.is_dir():
                continue

            stats["total_dirs"] += 1
            check_result = check_directory(content_dir, verbose)

            if check_result["valid"]:
                stats["valid_count"] += 1
            else:
                stats["invalid_count"] += 1
                entry = {
                    "path": str(content_dir),
                    "name": content_dir.name,
                    "date": date_dir.name,
                    "missing": check_result["missing"],
                    "size_info": check_result["size_info"],
                }
                stats["invalid_entries"].append(entry)

                if verbose:
                    print(f"❌ {content_dir.name}")
                    print(f"   缺失: {', '.join(check_result['missing'])}")

                # 生成修复命令
                if "rewritten.md" in check_result["missing"]:
                    transcript_path = content_dir / "transcript.md"
                    metadata_path = content_dir / "metadata.md"
                    rewritten_path = content_dir / "rewritten.md"

                    cmd = {
                        "type": "rewrite",
                        "transcript": str(transcript_path),
                        "metadata": str(metadata_path),
                        "output": str(rewritten_path),
                    }
                    stats["fix_commands"].append(cmd)

    return stats


def generate_fix_report(stats: dict) -> str:
    """生成修复报告"""
    report = []
    report.append("# 内容完整性修复报告")
    report.append("")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## 统计")
    report.append(f"- 总目录数: {stats['total_dirs']}")
    report.append(f"- 完整目录: {stats['valid_count']}")
    report.append(f"- 不完整目录: {stats['invalid_count']}")
    report.append("")

    if stats["invalid_entries"]:
        report.append("## 不完整的条目")
        report.append("")

        for entry in stats["invalid_entries"]:
            report.append(f"### {entry['name']}")
            report.append(f"- 日期: {entry['date']}")
            report.append(f"- 路径: `{entry['path']}`")
            report.append(f"- 缺失文件: {', '.join(entry['missing'])}")
            report.append("")

    if stats["fix_commands"]:
        report.append("## 修复命令")
        report.append("")
        report.append("```bash")

        for i, cmd in enumerate(stats["fix_commands"], 1):
            if cmd["type"] == "rewrite":
                report.append(f"# {i}. {Path(cmd['transcript']).parent.name}")
                report.append(
                    f'python3 -c "import rewrite_service; '
                    f"rewrite_service.rewrite_content("
                    f"'{cmd['transcript']}', "
                    f"'{cmd['metadata']}', "
                    f"'{cmd['output']}')\""
                )
                report.append("")

        report.append("```")

    return "\n".join(report)


def auto_fix_missing_rewritten(archive_root: str = "content_archive", days: int = 30):
    """
    自动修复缺失的 rewritten.md

    仅修复 rewritten.md 缺失的情况，不修改其他文件
    """
    import rewrite_service

    stats = scan_content_archive(archive_root, days=days, verbose=True)

    if not stats["fix_commands"]:
        print("\n✅ 没有需要修复的条目")
        return

    print(f"\n🔧 开始自动修复 {len(stats['fix_commands'])} 个缺失的 rewritten.md...")
    print("=" * 60)

    success_count = 0
    fail_count = 0

    for cmd in stats["fix_commands"]:
        content_name = Path(cmd["transcript"]).parent.name
        print(f"\n▶️ 正在处理: {content_name}")

        try:
            result = rewrite_service.rewrite_content(cmd["transcript"], cmd["metadata"], cmd["output"])

            if result:
                print(f"✅ 成功: {content_name}")
                success_count += 1
            else:
                print(f"❌ 失败: {content_name}")
                fail_count += 1

        except Exception as e:
            print(f"❌ 错误: {e}")
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"修复完成: {success_count} 成功, {fail_count} 失败")


def main():
    parser = argparse.ArgumentParser(description="内容完整性验证工具")
    parser.add_argument(
        "--days", "-d", type=int, default=30, help="检查最近 N 天的内容（默认 30，0 表示全部）"
    )
    parser.add_argument("--only-invalid", action="store_true", help="只显示不完整的条目")
    parser.add_argument("--fix", action="store_true", help="自动修复缺失的 rewritten.md")
    parser.add_argument("--report", action="store_true", help="生成修复报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument(
        "--archive-root", default="content_archive", help="内容存档根目录（默认 content_archive）"
    )

    args = parser.parse_args()

    print("🔍 扫描内容存档目录...")
    print(f"   日期范围: {'全部' if args.days == 0 else f'最近 {args.days} 天'}")
    print()

    stats = scan_content_archive(
        archive_root=args.archive_root, days=args.days, only_invalid=args.only_invalid, verbose=args.verbose
    )

    print("\n📊 统计结果:")
    print(f"   总目录数: {stats['total_dirs']}")
    print(f"   完整: {stats['valid_count']}")
    print(f"   不完整: {stats['invalid_count']}")

    if stats["invalid_entries"]:
        print(f"\n⚠️  发现 {len(stats['invalid_entries'])} 个不完整的条目")

        if args.report:
            report = generate_fix_report(stats)
            report_path = f"content_integrity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n📄 报告已保存至: {report_path}")

        if args.fix:
            print()
            auto_fix_missing_rewritten(archive_root=args.archive_root, days=args.days)
    else:
        print("\n✅ 所有内容都完整")


if __name__ == "__main__":
    main()
