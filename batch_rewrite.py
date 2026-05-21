#!/usr/bin/env python3
"""
批量重写脚本 (增强版)
支持分批执行、大文件检测和完整性检查
"""

import os
import sys
import time
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rewrite_service
from utils.content_validator import check_directory, scan_content_archive


# 阈值配置
LARGE_FILE_THRESHOLD_KB = 40  # 超过此大小认为是"大文件"，单独处理
BATCH_DELAY = 10  # 批次间延迟（秒）


def categorize_by_size(transcript_paths: list) -> dict:
    """
    按文件大小分类任务

    返回: {
        'small': [...],  # 小文件，普通批次处理
        'large': [...]   # 大文件，单独排队处理
    }
    """
    categories = {'small': [], 'large': []}

    for path in transcript_paths:
        size_kb = os.path.getsize(path) / 1024
        entry = {
            'transcript': path,
            'size_kb': size_kb
        }

        if size_kb > LARGE_FILE_THRESHOLD_KB:
            categories['large'].append(entry)
            print(f"📦 大文件 ({size_kb:.1f} KB): {Path(path).parent.name}")
        else:
            categories['small'].append(entry)

    return categories


def process_batch(tasks: list, dry_run: bool = False) -> dict:
    """
    处理一批 rewrite 任务

    Args:
        tasks: 任务列表，每个元素包含 transcript, metadata, output 路径
        dry_run: True 则只检查不执行

    Returns: {'success': int, 'failed': int, 'skipped': int}
    """
    results = {'success': 0, 'failed': 0, 'skipped': 0}

    for task in tasks:
        transcript_path = task['transcript']
        metadata_path = task['metadata']
        output_path = task['output']
        content_name = Path(transcript_path).parent.name

        print(f"\n▶️  处理: {content_name}")

        # 检查 transcript 是否存在
        if not os.path.exists(transcript_path):
            print(f"❌ Transcript 不存在: {transcript_path}")
            results['failed'] += 1
            continue

        # 二次检查：rewritten.md 是否已存在
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            if size > 100:  # 文件存在且有意义（非空）
                print(f"⏭️  已存在 rewritten.md ({size} bytes)，跳过")
                results['skipped'] += 1
                continue

        # 执行 rewrite
        if dry_run:
            print(f"🔍 [DRY RUN] 将会执行 rewrite: {transcript_path}")
            results['success'] += 1
        else:
            try:
                success = rewrite_service.rewrite_content(
                    transcript_path,
                    metadata_path,
                    output_path
                )

                if success:
                    print(f"✅ 成功: {content_name}")
                    results['success'] += 1
                else:
                    print(f"❌ 失败: {content_name}")
                    results['failed'] += 1

            except Exception as e:
                print(f"❌ 错误: {e}")
                results['failed'] += 1

    return results


def find_rewrite_tasks(archive_root: str = 'content_archive', days: int = 0) -> list:
    """
    扫描需要 rewrite 的内容

    Returns: [{'transcript': ..., 'metadata': ..., 'output': ...}]
    """
    tasks = []

    # 获取不完整的条目
    stats = scan_content_archive(
        archive_root=archive_root,
        days=days,
        only_invalid=False,
        verbose=False
    )

    for entry in stats['invalid_entries']:
        content_dir = Path(entry['path'])

        # 只处理 transcript 存在但 rewritten.md 缺失的情况
        transcript_path = content_dir / 'transcript.md'
        metadata_path = content_dir / 'metadata.md'
        output_path = content_dir / 'rewritten.md'

        if transcript_path.exists() and metadata_path.exists():
            tasks.append({
                'transcript': str(transcript_path),
                'metadata': str(metadata_path),
                'output': str(output_path),
                'date': entry['date'],
                'missing': entry['missing']
            })

    return tasks


def main():
    parser = argparse.ArgumentParser(
        description='批量重写脚本（增强版）'
    )
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=0,
        help='处理最近 N 天的内容（0 表示全部）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只检查不执行'
    )
    parser.add_argument(
        '--large-only',
        action='store_true',
        help='只处理大文件 (>40KB)'
    )
    parser.add_argument(
        '--small-only',
        action='store_true',
        help='只处理小文件 (<=40KB)'
    )
    parser.add_argument(
        '--archive-root',
        default='content_archive',
        help='内容存档根目录'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🚀 批量重写脚本（增强版）")
    print("=" * 60)
    print(f"日期范围: {'全部' if args.days == 0 else f'最近 {args.days} 天'}")
    print(f"模式: {'DRY RUN' if args.dry_run else '正式执行'}")
    print()

    # 扫描需要处理的任务
    print("🔍 扫描待处理内容...")
    all_tasks = find_rewrite_tasks(
        archive_root=args.archive_root,
        days=args.days
    )

    if not all_tasks:
        print("\n✅ 没有需要处理的内容")
        return

    print(f"找到 {len(all_tasks)} 个待处理内容")

    # 按大小分类
    transcript_paths = [t['transcript'] for t in all_tasks]
    categories = categorize_by_size(transcript_paths)

    print(f"\n📊 分类统计:")
    print(f"   小文件: {len(categories['small'])} 个")
    print(f"   大文件: {len(categories['large'])} 个")

    # 根据参数选择处理哪类
    tasks_to_process = []

    if args.large_only:
        tasks_to_process = categories['large']
        print("\n⚠️  只处理大文件")
    elif args.small_only:
        tasks_to_process = categories['small']
        print("\n⚠️  只处理小文件")
    else:
        # 默认：先处理小文件，再处理大文件
        tasks_to_process = categories['small'] + categories['large']

    if not tasks_to_process:
        print("\n✅ 没有匹配条件的任务")
        return

    print(f"\n将处理 {len(tasks_to_process)} 个任务")

    if args.dry_run:
        print("\n🔍 DRY RUN 模式预览:")
        for task in tasks_to_process:
            size_kb = task.get('size_kb', os.path.getsize(task['transcript']) / 1024)
            name = Path(task['transcript']).parent.name
            print(f"   - {name} ({size_kb:.1f} KB)")

        return

    # 执行处理
    print("\n" + "=" * 60)
    print("开始处理...")
    print("=" * 60)

    # 先处理小文件批次
    if categories['small']:
        print(f"\n📦 第一批次: 小文件 ({len(categories['small'])} 个)")
        small_transcripts = {x['transcript'] for x in categories['small']}
        small_tasks = [
            {
                'transcript': t['transcript'],
                'metadata': t['metadata'],
                'output': t['output']
            }
            for t in all_tasks
            if t['transcript'] in small_transcripts
        ]
        results1 = process_batch(small_tasks)

        print(f"\n小文件批次完成: {results1['success']} 成功, {results1['skipped']} 跳过, {results1['failed']} 失败")

        if categories['large']:
            print(f"\n⏳ 等待 {BATCH_DELAY} 秒后处理大文件批次...")
            time.sleep(BATCH_DELAY)

    # 再处理大文件批次（每个之间增加延迟）
    if categories['large']:
        print(f"\n📦 第二批次: 大文件 ({len(categories['large'])} 个)")
        large_transcripts = {x['transcript'] for x in categories['large']}
        large_tasks = [
            {
                'transcript': t['transcript'],
                'metadata': t['metadata'],
                'output': t['output']
            }
            for t in all_tasks
            if t['transcript'] in large_transcripts
        ]

        for i, task in enumerate(large_tasks, 1):
            print(f"\n[{i}/{len(large_tasks)}] 处理大文件任务")
            result = process_batch([task])
            time.sleep(BATCH_DELAY)

    # 总结
    print("\n" + "=" * 60)
    print("🎉 处理完成!")


if __name__ == "__main__":
    main()
