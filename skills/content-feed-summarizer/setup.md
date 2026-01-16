# Environment Setup Guide

To run the `content-feed-summarizer` skill, you need to install the following dependencies.

## 1. System Dependencies (FFmpeg)
Required for audio processing by Whisper and yt-dlp.

- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`
- **Windows**: `winget install ffmpeg`

## 2. Python Dependencies
Create a virtual environment and install the required packages:

```bash
# Create venv
python -m venv .venv
source .venv/bin/activate

# Install core tools
# pydub is required for audio chunking (Groq 25MB limit)
pip install yt-dlp youtube-transcript-api groq pydub

# Install XiaoYuZhou downloader
# (Assuming xyz-dl is available via git or pip, adjust if needed)
pip install git+https://github.com/shiquda/xyz-dl.git
```

## 3. API Keys Configuration
Set the following environment variables.

```bash
# Groq API (Required for Audio Transcription)
# Get key from: https://console.groq.com/keys
export GROQ_API_KEY="gsk_..."

# Gemini API (Required for cover generation)
export GOOGLE_API_KEY="your_gemini_api_key"

# Feishu (Optional)
export FEISHU_APP_ID="cli_..."
export FEISHU_APP_SECRET="..."
export FEISHU_TABLE_ID="tbl..."
```

## 4. Audio Processing Note
Since we are using Groq API, you do NOT need a GPU or heavy local models.
However, `ffmpeg` is still REQUIRED for `pydub` to split audio files.

