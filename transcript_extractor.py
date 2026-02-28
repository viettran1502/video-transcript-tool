#!/usr/bin/env python3
"""
Enhanced Multi-Platform Transcript Tool with Whisper Speech-to-Text
YouTube ✅ + TikTok ✅ + Facebook + Douyin + AUDIO TRANSCRIPTION 🎯

__author__ = "Trần Việt Anh (@viettran1502)"
__email__ = "viettran1502@gmail.com"
__contributors__ = ["Cot.ghw@gmail.com"]
__version__ = "1.0.0"
__license__ = "MIT"
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

from whisper_manager import preload_model, require_model

class WhisperTranscriptExtractor:
    def __init__(self, whisper_model='small'):
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

        # Whisper setup — background preload (non-blocking)
        self.whisper_model = whisper_model
        self.temp_dir = tempfile.mkdtemp(prefix='transcript_')

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

        preload_model(self.whisper_model)

    def _get_whisper(self):
        """Return the Whisper model, blocking until the background load finishes."""
        return require_model(self.whisper_model)
    
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
        """Extract audio from video using yt-dlp (16kHz mono wav — optimal for Whisper)"""
        try:
            audio_file = os.path.join(self.temp_dir, f"audio_{int(time.time())}.wav")

            cmd = [
                'yt-dlp', '--js-runtimes', 'node',
                '--remote-components', 'ejs:github',
                '--extract-audio',
                '--audio-format', 'wav',
                '--postprocessor-args', 'ffmpeg:-ar 16000 -ac 1',
                '--output', audio_file.replace('.wav', '.%(ext)s'),
                video_url
            ]

            self.logger.info(f"Extracting audio: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # Find the actual audio file (yt-dlp may change extension)
                for ext in ['wav', 'mp3', 'm4a', 'webm']:
                    potential_file = audio_file.replace('.wav', f'.{ext}')
                    if os.path.exists(potential_file):
                        self.logger.info(f"Audio extracted: {potential_file}")
                        return potential_file

                # If exact match not found, look for any audio file
                audio_dir = os.path.dirname(audio_file)
                for file in os.listdir(audio_dir):
                    if file.startswith('audio_') and file.endswith(('.wav', '.mp3', '.m4a', '.webm')):
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
        whisper = self._get_whisper()
        if not whisper:
            self.logger.warning("Whisper not available, skipping audio transcription")
            return None

        try:
            self.logger.info(f"Transcribing audio: {audio_file}")
            result = whisper.transcribe(audio_file, language="vi")
            
            transcript = result["text"].strip()
            self.logger.info(f"Transcription completed: {len(transcript)} characters")
            return transcript
            
        except Exception as e:
            self.logger.error(f"Audio transcription failed: {e}")
            return None
    
    @staticmethod
    def _parse_vtt(raw: str) -> str:
        """Convert VTT/SRT subtitle content to clean plain text."""
        lines = []
        seen = set()
        for line in raw.splitlines():
            line = line.strip()
            # Skip VTT headers, timestamps, and positioning metadata
            if not line or line.startswith(('WEBVTT', 'Kind:', 'Language:',
                                           'NOTE', 'STYLE')):
                continue
            if '-->' in line:
                continue
            if line.isdigit():
                continue
            # Strip VTT inline tags like <00:00:00.240><c>...</c>
            clean = re.sub(r'<[^>]+>', '', line).strip()
            if not clean:
                continue
            # Deduplicate consecutive identical lines (VTT repeats them)
            if clean not in seen:
                lines.append(clean)
                seen.add(clean)
            # Reset seen set periodically to handle recurring phrases
            if len(seen) > 200:
                seen.clear()
        return '\n'.join(lines)

    def _check_subtitles(self, url: str, video_id: str) -> Optional[Dict]:
        """Check for existing subtitles. Uses --print-to-file to get the
        title in the same yt-dlp call (zero extra cost)."""
        try:
            title_file = os.path.join(self.temp_dir, '.title.txt')
            cmd = [
                'yt-dlp', '--js-runtimes', 'node',
                '--remote-components', 'ejs:github',
                '--write-subs', '--write-auto-subs',
                '--sub-lang', 'vi,en', '--skip-download',
                '--print-to-file', 'title', title_file,
                '--paths', self.temp_dir,
                '-o', '%(id)s.%(ext)s',
                url
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Read title
            title = video_id
            if os.path.exists(title_file):
                try:
                    with open(title_file, 'r', encoding='utf-8') as fh:
                        title = fh.read().strip() or video_id
                except Exception:
                    pass
                os.remove(title_file)

            # Scan temp_dir for any subtitle file yt-dlp wrote
            for f in sorted(os.listdir(self.temp_dir)):
                if f.endswith(('.vtt', '.srt', '.ass')):
                    sub_path = os.path.join(self.temp_dir, f)
                    lang = "auto"
                    for l in ['vi', 'en']:
                        if f'.{l}.' in f:
                            lang = l
                            break
                    with open(sub_path, 'r', encoding='utf-8') as fh:
                        raw = fh.read()
                    os.remove(sub_path)
                    content = self._parse_vtt(raw)
                    if len(content.strip()) > 20:
                        return {
                            "success": True,
                            "title": title,
                            "transcript": content,
                            "source": f"yt-dlp_subs_{lang}",
                            "language": lang
                        }
        except Exception:
            pass
        return None

    def extract_youtube(self, url: str) -> Dict:
        """YouTube extraction — subtitle-first, audio+Whisper only if needed."""
        self._rate_limit('youtube')

        try:
            video_id_match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
            if not video_id_match:
                return {"error": "Invalid YouTube URL"}

            video_id = video_id_match.group(1)

            # Fast path: try subtitles first (single yt-dlp call, ~10s).
            sub_result = self._check_subtitles(url, video_id)
            if sub_result is not None:
                return sub_result

            # Slow path: no subtitles — download audio and transcribe.
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
    
    def _check_tiktok_subtitles(self, url: str) -> Optional[str]:
        """Try fetching TikTok auto-captions via yt-dlp."""
        try:
            cmd = [
                'yt-dlp', '--js-runtimes', 'node',
                '--remote-components', 'ejs:github',
                '--write-auto-subs',
                '--sub-lang', 'vi,en',
                '--skip-download',
                '--paths', self.temp_dir,
                '-o', '%(id)s.%(ext)s',
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                for f in os.listdir(self.temp_dir):
                    if f.endswith(('.vtt', '.srt', '.ass')):
                        sub_path = os.path.join(self.temp_dir, f)
                        with open(sub_path, 'r', encoding='utf-8') as fh:
                            raw = fh.read()
                        os.remove(sub_path)
                        content = self._parse_vtt(raw)
                        if len(content.strip()) > 20:
                            return content
        except Exception:
            pass
        return None

    def extract_tiktok(self, url: str) -> Dict:
        """Enhanced TikTok extraction — subtitle-first, then audio transcription"""
        self._rate_limit('tiktok')

        try:
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

                    # --- Subtitle-first: try auto-captions before Whisper ---
                    self.logger.info("Checking TikTok auto-captions...")
                    sub_text = self._check_tiktok_subtitles(url)
                    if sub_text:
                        full_content = f"{sub_text}\n\n--- Metadata ---\n{metadata}"
                        return {
                            "success": True,
                            "title": title,
                            "transcript": full_content,
                            "source": "yt-dlp_auto_subs+metadata",
                            "language": "auto"
                        }

                    # --- Fallback: audio transcription ---
                    self.logger.info("No auto-captions, extracting audio for transcription...")
                    audio_file = self.extract_audio(url)

                    if audio_file:
                        transcript = self.transcribe_audio(audio_file)
                        os.remove(audio_file)  # Cleanup

                        if transcript and len(transcript.strip()) > 10:
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
    
    def _resolve_facebook_url(self, url: str) -> str:
        """Resolve Facebook /share/v/ short links to their canonical URL."""
        if '/share/v/' in url:
            try:
                resp = requests.get(url, allow_redirects=True, timeout=10,
                                    headers={'User-Agent': 'curl/8.0'})
                resolved = resp.url.split('?')[0]
                if resolved != url:
                    self.logger.info(f"Resolved FB share URL → {resolved}")
                    return resolved
            except Exception:
                pass
        return url

    def extract_facebook(self, url: str) -> Dict:
        """Facebook extraction — subtitle-first via yt-dlp, then audio+Whisper."""
        self._rate_limit('facebook')
        url = self._resolve_facebook_url(url)

        # Try subtitles first (same approach as YouTube)
        video_id = re.search(r'/(?:videos|reel)/(\d+)', url)
        if not video_id:
            video_id = re.search(r'v=(\d+)', url)
        vid = video_id.group(1) if video_id else 'facebook'

        sub_result = self._check_subtitles(url, vid)
        if sub_result is not None:
            return sub_result

        # Fallback: download audio and transcribe with Whisper
        self.logger.info("No Facebook subtitles found, trying audio transcription...")
        audio_file = self.extract_audio(url)
        if audio_file:
            transcript = self.transcribe_audio(audio_file)
            os.remove(audio_file)
            if transcript:
                return {
                    "success": True,
                    "title": "Facebook Video (Audio Transcript)",
                    "transcript": transcript,
                    "source": "whisper_audio",
                    "language": "auto"
                }

        return {"error": "Could not extract subtitles or transcribe Facebook audio"}

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
    import argparse

    parser = argparse.ArgumentParser(description='Extract video transcripts with Whisper AI')
    parser.add_argument('url', help='Video URL (YouTube, TikTok, etc.)')
    parser.add_argument('--model', default='small',
                        help='Whisper model name (default: small). Use large-v3 for higher accuracy.')
    args = parser.parse_args()

    url = args.url
    extractor = WhisperTranscriptExtractor(whisper_model=args.model)

    try:
        print(f"Processing: {url}")
        result = extractor.extract_transcript(url)

        if "success" in result:
            print("\nSuccess!")
            print(f"Platform: {extractor.identify_platform(url).upper()}")
            print(f"Title: {result.get('title', 'N/A')}")
            print(f"Source: {result.get('source', 'N/A')}")
            print(f"Language: {result.get('language', 'N/A')}")
            print(f"Length: {len(result['transcript'])} characters")
            print(f"\nContent:\n{result['transcript'][:500]}{'...' if len(result['transcript']) > 500 else ''}")

            # Save to file
            filename = f"transcript_{extractor.identify_platform(url)}_{int(time.time())}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result['transcript'])
            print(f"Saved: {filename}")

        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

    finally:
        extractor.cleanup()

if __name__ == "__main__":
    main()
