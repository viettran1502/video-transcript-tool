#!/usr/bin/env python3
"""
Enhanced Multi-Platform Transcript Tool with Whisper Speech-to-Text
YouTube ✅ + TikTok ✅ + Facebook + Douyin + AUDIO TRANSCRIPTION 🎯
"""

import requests
import re
import json
import time
import os
import tempfile
import subprocess
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional
import logging

class WhisperTranscriptExtractor:
    def __init__(self, whisper_model='large-v3'):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Rate limiting
        self.last_request = {}
        self.min_delay = {
            'youtube': 2,
            'tiktok': 3,
            'facebook': 3,
            'douyin': 4
        }
        
        # Whisper setup
        self.whisper_model = whisper_model
        self.whisper = None
        self.temp_dir = tempfile.mkdtemp(prefix='transcript_')
        
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        
        # Initialize Whisper
        self._init_whisper()
    
    def _init_whisper(self):
        """Initialize Whisper model (lazy loading)"""
        try:
            import whisper
            self.logger.info(f"Loading Whisper model: {self.whisper_model}")
            self.whisper = whisper.load_model(self.whisper_model)
            self.logger.info("Whisper model loaded successfully!")
        except Exception as e:
            self.logger.error(f"Failed to load Whisper: {e}")
            self.whisper = None
    
    def _rate_limit(self, platform: str):
        """Rate limiting per platform"""
        now = time.time()
        if platform in self.last_request:
            elapsed = now - self.last_request[platform]
            if elapsed < self.min_delay[platform]:
                sleep_time = self.min_delay[platform] - elapsed
                time.sleep(sleep_time)
        
        self.last_request[platform] = time.time()
    
    def expand_shortened_url(self, url: str) -> str:
        """Expand shortened URLs like vt.tiktok.com, vm.tiktok.com"""
        if any(short in url for short in ['vt.tiktok.com', 'vm.tiktok.com']):
            try:
                import requests
                self.logger.info(f"Expanding shortened URL: {url}")
                response = requests.head(url, allow_redirects=True, timeout=15)
                expanded_url = response.url.split('?')[0]  # Remove tracking params
                self.logger.info(f"Expanded to: {expanded_url}")
                return expanded_url
            except Exception as e:
                self.logger.warning(f"URL expansion failed: {e}")
                return url
        return url

    def identify_platform(self, url: str) -> str:
        """Identify platform from URL"""
        domain = urlparse(url).netloc.lower()
        
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'youtube'
        elif 'tiktok.com' in domain:
            return 'tiktok'
        elif 'facebook.com' in domain or 'fb.watch' in domain:
            return 'facebook'
        elif 'douyin.com' in domain:
            return 'douyin'
        else:
            return 'unknown'
    
    def extract_audio(self, video_url: str) -> Optional[str]:
        """Extract audio from video using yt-dlp"""
        try:
            audio_file = os.path.join(self.temp_dir, f"audio_{int(time.time())}.mp3")
            
            cmd = [
                'yt-dlp',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '192K',
                '--output', audio_file.replace('.mp3', '.%(ext)s'),
                video_url
            ]
            
            self.logger.info(f"Extracting audio: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                # Find the actual audio file (yt-dlp may change extension)
                for ext in ['mp3', 'wav', 'm4a', 'webm']:
                    potential_file = audio_file.replace('.mp3', f'.{ext}')
                    if os.path.exists(potential_file):
                        self.logger.info(f"Audio extracted: {potential_file}")
                        return potential_file
                
                # If exact match not found, look for any audio file
                audio_dir = os.path.dirname(audio_file)
                for file in os.listdir(audio_dir):
                    if file.startswith('audio_') and file.endswith(('.mp3', '.wav', '.m4a', '.webm')):
                        audio_path = os.path.join(audio_dir, file)
                        self.logger.info(f"Found audio file: {audio_path}")
                        return audio_path
                
                self.logger.warning("Audio extraction completed but file not found")
                return None
            else:
                self.logger.error(f"Audio extraction failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("Audio extraction timed out")
            return None
        except Exception as e:
            self.logger.error(f"Audio extraction error: {e}")
            return None
    
    def transcribe_audio(self, audio_file: str) -> Optional[str]:
        """Transcribe audio using Whisper"""
        if not self.whisper:
            self.logger.warning("Whisper not available, skipping audio transcription")
            return None
        
        try:
            self.logger.info(f"Transcribing audio: {audio_file}")
            result = self.whisper.transcribe(audio_file, language="vi")
            
            transcript = result["text"].strip()
            self.logger.info(f"Transcription completed: {len(transcript)} characters")
            return transcript
            
        except Exception as e:
            self.logger.error(f"Audio transcription failed: {e}")
            return None
    
    def extract_youtube(self, url: str) -> Dict:
        """Enhanced YouTube extraction with audio transcription"""
        self._rate_limit('youtube')
        
        try:
            # Original subtitle extraction
            video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
            if not video_id_match:
                return {"error": "Invalid YouTube URL"}
            
            video_id = video_id_match.group(1)
            
            # Try original method first
            try:
                cmd = ['yt-dlp', '--write-subs', '--write-auto-subs', '--sub-lang', 'vi,en', '--skip-download', '--print', 'title', url]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout.strip():
                    title = result.stdout.strip()
                    
                    # Look for subtitle files
                    for lang in ['vi', 'en']:
                        sub_file = f"{video_id}.{lang}.vtt"
                        if os.path.exists(sub_file):
                            with open(sub_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            os.remove(sub_file)
                            return {
                                "success": True,
                                "title": title,
                                "transcript": content,
                                "source": f"yt-dlp_subs_{lang}",
                                "language": lang
                            }
            except:
                pass
            
            # If subtitles not available, extract audio and transcribe
            self.logger.info("No subtitles found, trying audio transcription...")
            audio_file = self.extract_audio(url)
            
            if audio_file:
                transcript = self.transcribe_audio(audio_file)
                os.remove(audio_file)  # Cleanup
                
                if transcript:
                    return {
                        "success": True,
                        "title": "YouTube Video (Audio Transcript)",
                        "transcript": transcript,
                        "source": "whisper_audio",
                        "language": "auto"
                    }
            
            return {"error": "Could not extract subtitles or transcribe audio"}
            
        except Exception as e:
            return {"error": f"YouTube extraction failed: {str(e)}"}
    
    def extract_tiktok(self, url: str) -> Dict:
        """Enhanced TikTok extraction with audio transcription"""
        self._rate_limit('tiktok')
        
        try:
            # Original metadata extraction
            video_id_match = re.search(r'/video/(\d+)', url)
            if not video_id_match:
                return {"error": "Could not find TikTok video ID"}
            
            video_id = video_id_match.group(1)
            
            try:
                cmd = ['yt-dlp', '--print', 'title,uploader,upload_date', url]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    title = lines[0] if len(lines) > 0 else ""
                    uploader = lines[1] if len(lines) > 1 else ""
                    upload_date = lines[2] if len(lines) > 2 else ""
                    
                    metadata = f"{title}. Creator: @{uploader}. Posted: {upload_date}"
                    
                    # Try audio transcription
                    self.logger.info("Extracting audio for transcription...")
                    audio_file = self.extract_audio(url)
                    
                    if audio_file:
                        transcript = self.transcribe_audio(audio_file)
                        os.remove(audio_file)  # Cleanup
                        
                        if transcript and len(transcript.strip()) > 10:
                            # Combine metadata + transcript
                            full_content = f"{transcript}\n\n--- Metadata ---\n{metadata}"
                            return {
                                "success": True,
                                "title": title,
                                "transcript": full_content,
                                "source": "whisper_audio+metadata",
                                "language": "auto"
                            }
                    
                    # Fallback to metadata only
                    return {
                        "success": True,
                        "title": title,
                        "transcript": metadata,
                        "source": "yt-dlp_metadata",
                        "language": "auto"
                    }
                    
            except Exception as e:
                self.logger.error(f"TikTok extraction error: {e}")
            
            return {"error": "TikTok extraction failed"}
            
        except Exception as e:
            return {"error": f"TikTok processing failed: {str(e)}"}
    
    def extract_transcript(self, url: str) -> Dict:
        """Main method to extract transcript from any platform"""
        # Expand shortened URLs first
        url = self.expand_shortened_url(url)
        platform = self.identify_platform(url)
        self.logger.info(f"Processing {platform} video: {url.split('/')[-1][:20]}...")
        
        if platform == 'youtube':
            return self.extract_youtube(url)
        elif platform == 'tiktok':
            return self.extract_tiktok(url)
        elif platform == 'facebook':
            return {"error": "Facebook support not implemented yet"}
        elif platform == 'douyin':
            return {"error": "Douyin support not implemented yet"}
        else:
            return {"error": f"Unsupported platform: {platform}"}
    
    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 transcript_tool_whisper.py <video_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    extractor = WhisperTranscriptExtractor(whisper_model='large-v3')
    
    try:
        print(f"🚀 Processing: {url}")
        result = extractor.extract_transcript(url)
        
        if "success" in result:
            print("\n✅ Success!")
            print(f"📱 Platform: {extractor.identify_platform(url).upper()}")
            print(f"🎬 Title: {result.get('title', 'N/A')}")
            print(f"📝 Source: {result.get('source', 'N/A')}")
            print(f"🔤 Language: {result.get('language', 'N/A')}")
            print(f"📄 Length: {len(result['transcript'])} characters")
            print(f"\n📋 Content:\n{result['transcript'][:500]}{'...' if len(result['transcript']) > 500 else ''}")
            
            # Save to file
            filename = f"transcript_{extractor.identify_platform(url)}_{int(time.time())}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result['transcript'])
            print(f"💾 Saved: {filename}")
            
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    main()
