# Video Transcript Tool 🎬

Extract transcripts from video URLs across multiple platforms using Whisper AI.

## ✨ Features

- **YouTube** ✅ Full transcript support
- **TikTok** ✅ Audio extraction + transcription  
- **Facebook** ⚠️ Limited support (metadata)
- **Douyin** ⚠️ Limited support (metadata)
- **Whisper AI** integration for accurate speech-to-text
- **CLI** interface for automation
- **Web interface** available (separate deployment)

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- FFmpeg (for audio processing)
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/viettran1502/video-transcript-tool.git
cd video-transcript-tool

# Create virtual environment
python3 -m venv whisper-venv
source whisper-venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Whisper
pip install git+https://github.com/openai/whisper.git
```

### Usage

```bash
# Extract transcript from YouTube
python3 transcript_extractor.py "https://youtube.com/watch?v=VIDEO_ID"

# Extract from TikTok
python3 transcript_extractor.py "https://tiktok.com/@user/video/123456"

# Extract from Facebook (limited)
python3 facebook_direct_fixed.py "https://facebook.com/watch/123456"
```

## 📁 File Structure

```
video-transcript-tool/
├── transcript_extractor.py    # Main CLI tool (YouTube + TikTok)
├── facebook_direct_fixed.py   # Facebook extractor
├── douyin_breakthrough.py     # Douyin extractor  
├── requirements.txt           # Python dependencies
├── README.md                 # This file
└── examples/                 # Usage examples
```

## 🔧 Technical Details

- **Whisper Model**: large-v3 (configurable)
- **Audio Format**: WAV 16kHz mono
- **Timeout**: 300s for YouTube, 180s for TikTok
- **Rate Limiting**: Built-in delays between requests
- **Temp Files**: Auto-cleanup after processing

## 🌐 Web Interface

For a user-friendly web interface, check out the companion webapp:
- Real-time progress updates
- Batch processing support
- Mobile-friendly design
- Socket.IO integration

## 📋 Requirements

- `whisper` - OpenAI's speech recognition
- `yt-dlp` - YouTube/platform downloader  
- `requests` - HTTP client
- `beautifulsoup4` - HTML parsing
- `selenium` - Web automation (Facebook/Douyin)
- `ffmpeg-python` - Audio processing

## 🛠️ Development

```bash
# Run with debug logging
export DEBUG=1
python3 transcript_extractor.py "VIDEO_URL"

# Test specific platform
python3 facebook_direct_fixed.py "FACEBOOK_URL"
python3 douyin_breakthrough.py "DOUYIN_URL"
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit your changes  
4. Push to the branch
5. Create Pull Request

## 📄 License

MIT License - see LICENSE file for details.

## 🙋‍♂️ Author

**Trần Việt Anh** (@viettran1502)
- Telegram: @viettran1502
- Email: viettran1502@gmail.com

---

⭐ If this tool helps you, please give it a star!
