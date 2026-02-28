#!/usr/bin/env python3
"""
Basic Usage Examples for Video Transcript Tool

__author__ = "Trần Việt Anh (@viettran1502)"
__email__ = "viettran1502@gmail.com"
__contributors__ = ["Cot.ghw@gmail.com"]
__version__ = "1.0.0"
__license__ = "MIT"

"""

import sys
import os

# Add parent directory to path to import transcript_extractor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transcript_extractor import WhisperTranscriptExtractor

def main():
    # Initialize extractor — constructor returns instantly (Whisper loads in background).
    # The model is only needed when audio transcription is required (no subtitles found).
    extractor = WhisperTranscriptExtractor(whisper_model='small')  # 'small' balances speed & accuracy
    
    # Example URLs (replace with real ones)
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    tiktok_url = "https://www.tiktok.com/@user/video/1234567890"
    
    print("🎬 Video Transcript Tool Examples\n")
    
    # YouTube example
    print("📹 Extracting YouTube transcript...")
    try:
        result = extractor.extract_youtube_transcript(youtube_url)
        if result.get('transcript'):
            print(f"✅ Success: {len(result['transcript'])} characters")
            print(f"📝 Preview: {result['transcript'][:200]}...")
        else:
            print("❌ Failed to extract transcript")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # TikTok example  
    print("🎵 Extracting TikTok transcript...")
    try:
        result = extractor.extract_tiktok_transcript(tiktok_url)
        if result.get('transcript'):
            print(f"✅ Success: {len(result['transcript'])} characters")
            print(f"📝 Preview: {result['transcript'][:200]}...")
        else:
            print("❌ Failed to extract transcript")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
