import rewrite_service
import os

tasks = [
    {
        "transcript": "content_archive/2025-11-25/xiaoyuzhou_忽左忽右_午后偏见043｜当博物馆开始说话：薛茗谈展品背后的文化、权力与记忆/transcript.md",
        "metadata": "content_archive/2025-11-25/xiaoyuzhou_忽左忽右_午后偏见043｜当博物馆开始说话：薛茗谈展品背后的文化、权力与记忆/metadata.md",
        "output": "content_archive/2025-11-25/xiaoyuzhou_忽左忽右_午后偏见043｜当博物馆开始说话：薛茗谈展品背后的文化、权力与记忆/rewritten.md"
    },
    {
        "transcript": "content_archive/2023-10-31/xiaoyuzhou_忽左忽右_午后偏见030厌女、母职与消失的女性/transcript.md",
        "metadata": "content_archive/2023-10-31/xiaoyuzhou_忽左忽右_午后偏见030厌女、母职与消失的女性/metadata.md",
        "output": "content_archive/2023-10-31/xiaoyuzhou_忽左忽右_午后偏见030厌女、母职与消失的女性/rewritten.md"
    }
]

for task in tasks:
    print(f"Processing {task['metadata']}...")
    if os.path.exists(task['transcript']):
        rewrite_service.rewrite_content(task['transcript'], task['metadata'], task['output'])
    else:
        print(f"❌ Transcript not found: {task['transcript']}")
