#!/usr/bin/env python3
"""

__author__ = "Trần Việt Anh (@viettran1502)"
__email__ = "viettran1502@gmail.com"
__contributors__ = ["Cot.ghw@gmail.com"]
__version__ = "1.0.0"
__license__ = "MIT"

Douyin Breakthrough: Multiple attack vectors for Chinese platform
"""

import os
import re
import time
import json
import requests
import subprocess
import tempfile
import random
from urllib.parse import urlparse, unquote

from whisper_manager import preload_model, require_model

class DouyinBreakthrough:
    def __init__(self, whisper_model='small'):
        self.temp_dir = tempfile.mkdtemp(prefix='douyin_')
        self.session = requests.Session()
        self.whisper_model = whisper_model

        # Chinese-friendly user agents
        self.user_agents = [
            'Mozilla/5.0 (Linux; Android 11; ONEPLUS A6000) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.74 Mobile Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.85 Mobile Safari/537.36'
        ]

        preload_model(self.whisper_model)
        self._setup_session()

    def _get_whisper(self):
        """Return the shared Whisper model, blocking until ready."""
        return require_model(self.whisper_model)
    
    def _setup_session(self):
        ua = random.choice(self.user_agents)
        
        self.session.headers.update({
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache'
        })
    
    def _extract_video_id(self, url):
        """Extract video ID from Douyin URL"""
        patterns = [
            r'/video/(\d+)',
            r'modal_id=(\d+)',
            r'/(\d+)/?$',
            r'v\.douyin\.com/([A-Za-z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def method_api_reverse_engineering(self, video_id):
        """Try to reverse engineer Douyin API endpoints"""
        try:
            print("🔍 API reverse engineering attack...")
            
            # Common Douyin API endpoints
            api_endpoints = [
                f"https://www.douyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}",
                f"https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids={video_id}",
                f"https://aweme.snssdk.com/aweme/v1/aweme/detail/?aweme_id={video_id}",
                f"https://aweme-eagle.snssdk.com/aweme/v1/play/?video_id={video_id}"
            ]
            
            for api_url in api_endpoints:
                try:
                    # Add Chinese headers
                    headers = self.session.headers.copy()
                    headers.update({
                        'Referer': 'https://www.douyin.com/',
                        'Origin': 'https://www.douyin.com',
                        'X-Requested-With': 'XMLHttpRequest'
                    })
                    
                    response = self.session.get(api_url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            
                            if 'aweme_list' in data and data['aweme_list']:
                                aweme = data['aweme_list'][0]
                                
                                # Extract video info
                                title = aweme.get('desc', 'Douyin Video')
                                author = aweme.get('author', {}).get('nickname', '')
                                
                                # Extract video URLs
                                video_urls = []
                                if 'video' in aweme:
                                    video_info = aweme['video']
                                    
                                    # Try different video quality URLs
                                    url_keys = ['play_addr', 'download_addr', 'play_addr_lowbr']
                                    for url_key in url_keys:
                                        if url_key in video_info and 'url_list' in video_info[url_key]:
                                            video_urls.extend(video_info[url_key]['url_list'])
                                
                                if video_urls:
                                    return {
                                        'success': True,
                                        'method': 'api-reverse-engineering',
                                        'title': title,
                                        'author': author,
                                        'video_urls': video_urls,
                                        'api_endpoint': api_url
                                    }
                                    
                        except json.JSONDecodeError:
                            # Maybe it's not JSON, try to parse as text
                            content = response.text
                            
                            # Look for video URLs in response text
                            video_patterns = [
                                r'"play_addr":{[^}]*"url_list":\["([^"]+)"',
                                r'"download_addr":{[^}]*"url_list":\["([^"]+)"',
                                r'"url":"([^"]*\.mp4[^"]*)',
                                r'"video_url":"([^"]+)"'
                            ]
                            
                            for pattern in video_patterns:
                                matches = re.findall(pattern, content)
                                if matches:
                                    return {
                                        'success': True,
                                        'method': 'api-text-extraction',
                                        'video_urls': matches,
                                        'api_endpoint': api_url
                                    }
                                    
                except Exception as e:
                    print(f"API endpoint {api_url} failed: {e}")
                    continue
                    
        except Exception as e:
            print(f"API reverse engineering failed: {e}")
        
        return {'success': False}
    
    def method_douyin_webapp_scraping(self, video_id):
        """Scrape Douyin web app"""
        try:
            print("🔍 Web app scraping attack...")
            
            # Try different Douyin URLs
            douyin_urls = [
                f"https://www.douyin.com/video/{video_id}",
                f"https://www.iesdouyin.com/share/video/{video_id}",
                f"https://v.douyin.com/{video_id}"
            ]
            
            for url in douyin_urls:
                try:
                    headers = self.session.headers.copy()
                    headers.update({
                        'Referer': 'https://www.douyin.com/',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                    })
                    
                    response = self.session.get(url, headers=headers, timeout=20)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Enhanced patterns for 2024 Douyin structure
                        video_patterns = [
                            r'"playAddr":\[{"src":"([^"]+)"',
                            r'"download_addr":{"url_list":\["([^"]+)"',
                            r'"play_addr":{"url_list":\["([^"]+)"',
                            r'"url":"([^"]*v\.douyin\.com[^"]*\.mp4[^"]*)',
                            r'"src":"([^"]*aweme[^"]*\.mp4[^"]*)',
                            r'videoUrl":"([^"]+)"'
                        ]
                        
                        found_urls = []
                        for pattern in video_patterns:
                            matches = re.findall(pattern, content)
                            for match in matches:
                                if 'http' in match:
                                    found_urls.append(match)
                        
                        # Title extraction
                        title_patterns = [
                            r'"desc":"([^"]+)"',
                            r'<title[^>]*>([^<]+)</title>',
                            r'"aweme_detail":{[^}]*"desc":"([^"]+)"'
                        ]
                        
                        title = "Douyin Video"
                        for pattern in title_patterns:
                            match = re.search(pattern, content)
                            if match:
                                potential_title = match.group(1).strip()
                                if len(potential_title) > 5:
                                    title = potential_title[:100]
                                    break
                        
                        if found_urls:
                            return {
                                'success': True,
                                'method': 'webapp-scraping',
                                'title': title,
                                'video_urls': found_urls,
                                'url_used': url
                            }
                            
                except Exception as e:
                    print(f"Douyin URL {url} failed: {e}")
                    continue
                    
        except Exception as e:
            print(f"Web app scraping failed: {e}")
        
        return {'success': False}
    
    def method_you_get_enhanced(self, url):
        """Enhanced you-get with better error handling"""
        try:
            print("🔍 Enhanced you-get attack...")
            
            # Try you-get with different parameters
            you_get_commands = [
                ['you-get', '--json', url],
                ['you-get', '--info', url],
                ['you-get', '-i', url],
                ['you-get', '--format=mp4', url]
            ]
            
            for cmd in you_get_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        output = result.stdout
                        
                        # Try to parse as JSON first
                        try:
                            data = json.loads(output)
                            if 'streams' in data:
                                streams = data['streams']
                                video_urls = []
                                
                                for format_key in streams:
                                    stream = streams[format_key]
                                    if 'src' in stream:
                                        if isinstance(stream['src'], list):
                                            video_urls.extend(stream['src'])
                                        else:
                                            video_urls.append(stream['src'])
                                
                                if video_urls:
                                    return {
                                        'success': True,
                                        'method': 'you-get-enhanced',
                                        'title': data.get('title', 'Douyin Video'),
                                        'video_urls': video_urls
                                    }
                        except json.JSONDecodeError:
                            # Parse as text output
                            if 'http' in output:
                                # Extract URLs from text
                                url_matches = re.findall(r'http[s]?://[^\s<>"]+', output)
                                video_urls = [url for url in url_matches if '.mp4' in url or 'video' in url]
                                
                                if video_urls:
                                    return {
                                        'success': True,
                                        'method': 'you-get-text-parse',
                                        'video_urls': video_urls
                                    }
                                    
                except subprocess.TimeoutExpired:
                    print(f"you-get command timed out: {cmd}")
                    continue
                except Exception as e:
                    print(f"you-get command failed: {e}")
                    continue
                    
        except Exception as e:
            print(f"Enhanced you-get failed: {e}")
        
        return {'success': False}
    
    @staticmethod
    def _parse_vtt(raw):
        """Convert VTT/SRT subtitle content to clean plain text."""
        lines, seen = [], set()
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith(('WEBVTT', 'Kind:', 'Language:', 'NOTE', 'STYLE')):
                continue
            if '-->' in line or line.isdigit():
                continue
            clean = re.sub(r'<[^>]+>', '', line).strip()
            if clean and clean not in seen:
                lines.append(clean)
                seen.add(clean)
            if len(seen) > 200:
                seen.clear()
        return '\n'.join(lines)

    def _check_subtitles(self, url):
        """Try fetching existing subtitles via yt-dlp before heavier methods."""
        try:
            cmd = [
                'yt-dlp', '--js-runtimes', 'node',
                '--remote-components', 'ejs:github',
                '--write-subs', '--write-auto-subs',
                '--sub-lang', 'zh,en', '--skip-download',
                '--paths', self.temp_dir,
                '-o', '%(id)s.%(ext)s',
                url
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            for f in os.listdir(self.temp_dir):
                if f.endswith(('.vtt', '.srt', '.ass')):
                    sub_path = os.path.join(self.temp_dir, f)
                    with open(sub_path, 'r', encoding='utf-8') as fh:
                        raw = fh.read()
                    os.remove(sub_path)
                    content = self._parse_vtt(raw)
                    if len(content.strip()) > 20:
                        return {
                            'success': True,
                            'title': 'Douyin Video',
                            'transcript': content,
                            'source': 'douyin_yt-dlp_subs',
                            'language': 'zh'
                        }
        except Exception:
            pass
        return None

    def extract_douyin_breakthrough(self, url):
        """Main Douyin extraction method"""
        print(f"🚀 Douyin Breakthrough Attack: {url}")

        # --- Subtitle-first: fast path ---
        sub_result = self._check_subtitles(url)
        if sub_result:
            print("✅ Subtitles found — skipping heavy extraction")
            return sub_result

        video_id = self._extract_video_id(url)
        if not video_id:
            print("⚠️ Could not extract video ID, trying with full URL")
            video_id = url  # Use full URL as fallback
        else:
            print(f"🎯 Video ID: {video_id}")

        # Attack methods
        methods = [
            lambda: self.method_api_reverse_engineering(video_id),
            lambda: self.method_douyin_webapp_scraping(video_id),
            lambda: self.method_you_get_enhanced(url)
        ]
        
        successful_method = None
        
        for i, method in enumerate(methods, 1):
            method_name = method.__code__.co_name.replace('method_', '') if hasattr(method, '__code__') else f"method_{i}"
            print(f"\n🔥 Douyin Attack {i}: {method_name}")
            
            try:
                result = method()
                if result['success']:
                    print(f"✅ Attack {i} BREAKTHROUGH!")
                    successful_method = result
                    break
                else:
                    print(f"❌ Attack {i} blocked")
            except Exception as e:
                print(f"💥 Attack {i} error: {e}")
                continue
        
        if not successful_method:
            # Fallback: basic title extraction
            try:
                print("\n🔄 Fallback: Basic title extraction")
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text)
                    title = title_match.group(1).strip() if title_match else "Douyin Video"
                    
                    return {
                        'success': True,
                        'title': title,
                        'transcript': f"Douyin Video: {title} (Video extraction blocked - title only)",
                        'source': 'douyin_fallback_title',
                        'method': 'fallback-title-extraction'
                    }
            except:
                pass
                
            return {'success': False, 'error': 'ALL DOUYIN ATTACKS FAILED'}
        
        # Process successful result
        title = successful_method.get('title', 'Douyin Video')
        video_urls = successful_method.get('video_urls', [])
        author = successful_method.get('author', '')
        
        print(f"📝 Title: {title}")
        print(f"👤 Author: {author}")
        print(f"🎬 Video URLs found: {len(video_urls)}")
        
        # Try transcription
        transcript = None
        successful_video_url = None
        
        for i, video_url in enumerate(video_urls):
            print(f"\n🎯 Transcribing URL {i+1}/{len(video_urls)}: {video_url[:60]}...")
            
            try:
                audio_file = self._download_and_extract_audio(video_url)
                if audio_file:
                    transcript = self._transcribe_audio(audio_file)
                    if transcript and len(transcript.strip()) > 20:
                        successful_video_url = video_url
                        print(f"🎉 DOUYIN TRANSCRIPTION SUCCESS!")
                        break
                    else:
                        print(f"⚠️ Transcript too short")
                else:
                    print(f"❌ Audio extraction failed")
            except Exception as e:
                print(f"❌ Processing error: {e}")
                continue
        
        # Final result
        result = {
            'success': True,
            'title': title,
            'author': author,
            'method': f"douyin-{successful_method['method']}",
            'video_urls_found': len(video_urls)
        }
        
        if transcript:
            result['transcript'] = transcript
            result['source'] = 'douyin_breakthrough_whisper'
            result['successful_video_url'] = successful_video_url[:60] + '...'
            result['language'] = 'zh'
            print(f"\n🏆 DOUYIN VICTORY! {len(transcript)} chars transcribed!")
        else:
            metadata = f"Douyin Video: {title}"
            if author:
                metadata += f" by {author}"
            metadata += f" (Found {len(video_urls)} video URLs but transcription failed)"
            
            result['transcript'] = metadata
            result['source'] = 'douyin_breakthrough_metadata'
            print(f"\n⚠️ PARTIAL: URLs found but transcription failed")
        
        return result
    
    def _download_and_extract_audio(self, video_url):
        """Download and extract audio from Douyin video (16kHz mono wav)"""
        try:
            audio_file = os.path.join(self.temp_dir, f"douyin_audio_{int(time.time())}.wav")

            # yt-dlp with Douyin-specific settings — 16kHz mono for Whisper
            cmd = [
                'yt-dlp',
                '--extract-audio',
                '--audio-format', 'wav',
                '--postprocessor-args', 'ffmpeg:-ar 16000 -ac 1',
                '--user-agent', random.choice(self.user_agents),
                '--add-header', 'Referer: https://www.douyin.com/',
                '--no-check-certificate',
                '--ignore-errors',
                '--output', audio_file.replace('.wav', '.%(ext)s'),
                video_url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                for ext in ['wav', 'mp3', 'm4a']:
                    test_file = audio_file.replace('.wav', f'.{ext}')
                    if os.path.exists(test_file):
                        return test_file
            
            # Direct download fallback
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://www.douyin.com/',
                'Accept': '*/*'
            }

            video_file = audio_file.replace('.wav', '.mp4')
            response = self.session.get(video_url, headers=headers, stream=True, timeout=30)

            if response.status_code in [200, 206]:
                with open(video_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Extract audio — 16kHz mono wav
                ffmpeg_cmd = [
                    'ffmpeg', '-i', video_file,
                    '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-y',
                    audio_file
                ]
                
                ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=30)
                
                if os.path.exists(video_file):
                    os.remove(video_file)
                
                if ffmpeg_result.returncode == 0 and os.path.exists(audio_file):
                    return audio_file
            
        except Exception as e:
            print(f"❌ Douyin download failed: {e}")
        
        return None
    
    def _transcribe_audio(self, audio_file):
        """Transcribe with Whisper"""
        whisper = self._get_whisper()
        if not whisper:
            return None

        try:
            result = whisper.transcribe(audio_file, language="zh")
            transcript = result["text"].strip()
            
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            return transcript
            
        except Exception as e:
            print(f"❌ Douyin transcription failed: {e}")
            if os.path.exists(audio_file):
                os.remove(audio_file)
            return None
    
    def cleanup(self):
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass

def main():
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 douyin_breakthrough.py <douyin_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    extractor = DouyinBreakthrough()
    
    try:
        result = extractor.extract_douyin_breakthrough(url)
        
        if result['success']:
            print(f"\n🎉 DOUYIN BREAKTHROUGH SUCCESSFUL!")
            print(f"📱 Platform: DOUYIN")
            print(f"🎬 Title: {result['title']}")
            print(f"👤 Author: {result.get('author', 'N/A')}")
            print(f"📝 Source: {result['source']}")
            print(f"📄 Length: {len(result['transcript'])} chars")
            
            preview = result['transcript'][:300] + "..." if len(result['transcript']) > 300 else result['transcript']
            print(f"\n📋 TRANSCRIPT:")
            print(f"\"{preview}\"")
            
            filename = f"transcript_douyin_breakthrough_{int(time.time())}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result['transcript'])
            print(f"\n💾 Saved: {filename}")
            
        else:
            print(f"\n❌ DOUYIN DEFENSES TOO STRONG: {result.get('error')}")
    
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    main()
