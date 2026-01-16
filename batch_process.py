import subprocess
import time

tasks = [
    # 小宇宙
    ("python3 process_podcast.py https://www.xiaoyuzhoufm.com/episode/67443d70633b4594c979435b", "午后偏见043"),
    ("python3 process_podcast.py https://www.xiaoyuzhoufm.com/episode/653f5120257e3e0019688a2e", "午后偏见030"),
    ("python3 process_podcast.py https://www.xiaoyuzhoufm.com/episode/6135d99c54d197b99194e630", "午后偏见009"),
    # YouTube
    ("python3 process_video.py https://www.youtube.com/watch?v=0mrko3cYqBs", "失衡的乌托邦"),
    ("python3 process_video.py https://www.youtube.com/watch?v=DFyc0rFBptE", "失控的芬太尼"),
    ("python3 process_video.py https://www.youtube.com/watch?v=8uHur4G1ZVI", "镜像世界"),
]

print(f"🚀 Starting batch processing of {len(tasks)} items...", flush=True)

for cmd, name in tasks:
    print(f"\n--------------------------------------------------", flush=True)
    print(f"▶️ Processing: {name}", flush=True)
    print(f"   Command: {cmd}", flush=True)
    print(f"--------------------------------------------------\n", flush=True)
    
    try:
        # 使用 shell=True 来执行完整命令字符串
        process = subprocess.run(cmd, shell=True, check=False)
        if process.returncode == 0:
            print(f"\n✅ Successfully processed: {name}", flush=True)
        else:
            print(f"\n❌ Failed to process: {name} (Exit code: {process.returncode})", flush=True)
    except Exception as e:
        print(f"\n❌ Error executing {name}: {e}", flush=True)
    
    # 稍微等待一下，避免 API 速率限制
    time.sleep(5)

print("\n🎉 Batch processing complete!", flush=True)
