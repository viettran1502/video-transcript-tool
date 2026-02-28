#!/usr/bin/env python3
"""

__author__ = "Trần Việt Anh (@viettran1502)"
__email__ = "viettran1502@gmail.com"
__contributors__ = ["Cot.ghw@gmail.com"]
__version__ = "1.0.0"
__license__ = "MIT"

Facebook Direct Attack: Bypass restrictions với mobile tricks + API reverse engineering
"""

import os
import re
import time
import json
import requests
import subprocess
import tempfile
from urllib.parse import urlparse, unquote, parse_qs
import base64
import random

from whisper_manager import preload_model, require_model

class FacebookDirectAttack:
    def __init__(self, whisper_model='small'):
        self.temp_dir = tempfile.mkdtemp(prefix='fb_direct_')
        self.session = requests.Session()
        self.whisper_model = whisper_model

        # Multiple realistic mobile user agents
        self.user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
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
            'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def _extract_video_id(self, url):
        patterns = [
            r'/videos/(\d+)',
            r'v=(\d+)',
            r'/(\d+)/?$',
            r'/watch/?\?v=(\d+)',
            r'/reel/(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def method_mobile_webapp_extraction(self, video_id):
        """Advanced mobile webapp extraction"""
        try:
            mobile_urls = [
                f"https://m.facebook.com/watch/?v={video_id}",
                f"https://m.facebook.com/video.php?v={video_id}",
                f"https://touch.facebook.com/watch/?v={video_id}",
                f"https://mbasic.facebook.com/watch/?v={video_id}"
            ]
            
            for url_template in mobile_urls:
                try:
                    print(f"🔍 Trying: {url_template}")
                    
                    headers = self.session.headers.copy()
                    headers.update({
                        'Referer': 'https://www.google.com/',
                        'Origin': 'https://m.facebook.com'
                    })
                    
                    response = self.session.get(url_template, headers=headers, timeout=20)
                    
                    if response.status_code == 200:
                        content = response.text
                        
                        # Video URL patterns (fixed)
                        video_patterns = [
                            r'"playable_url":"([^"]+)"',
                            r'"src":"([^"]+\.mp4[^"]*)',
                            r'"hd_src":"([^"]+)"',
                            r'"sd_src":"([^"]+)"',
                            r'"url":"([^"]*scontent[^"]*\.mp4[^"]*)',
                            r'"url":"([^"]*fbcdn[^"]*\.mp4[^"]*)',
                            r'"contentUrl":"([^"]+\.mp4[^"]*)',
                            r'"videoData":{[^}]*"url":"([^"]+)"',
                            r'"video_url":"([^"]+)"'
                        ]
                        
                        found_urls = []
                        for pattern in video_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                clean_url = match.replace('\\/', '/').replace('\\u0026', '&')
                                if 'http' in clean_url and ('.mp4' in clean_url or 'video' in clean_url):
                                    found_urls.append(clean_url)
                        
                        # Title extraction
                        title = "Facebook Video"
                        title_patterns = [
                            r'<title[^>]*>([^<]+)</title>',
                            r'property="og:title"[^>]*content="([^"]+)"',
                            r'"title":"([^"]+)"'
                        ]
                        
                        for pattern in title_patterns:
                            match = re.search(pattern, content, re.IGNORECASE)
                            if match:
                                potential_title = match.group(1).strip()
                                if potential_title and len(potential_title) > 5:
                                    title = potential_title[:200]
                                    break
                        
                        if found_urls:
                            print(f"✅ Found {len(found_urls)} video URLs!")
                            return {
                                'success': True,
                                'method': 'mobile-webapp-enhanced',
                                'title': title,
                                'video_urls': found_urls,
                                'url_used': url_template
                            }
                            
                except Exception as e:
                    print(f"❌ Mobile URL {url_template} failed: {e}")
                    continue
                    
        except Exception as e:
            print(f"Mobile webapp extraction failed: {e}")
        
        return {'success': False}
    
    def method_graph_api_attack(self, video_id):
        """Facebook Graph API attack"""
        try:
            endpoints = [
                f"https://graph.facebook.com/v18.0/{video_id}",
                f"https://graph.facebook.com/{video_id}?fields=source,title,description",
                f"https://graph.facebook.com/v18.0/{video_id}?fields=source"
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        
                        if 'error' not in data and ('source' in data or 'title' in data):
                            return {
                                'success': True,
                                'method': 'graph-api-attack',
                                'data': data
                            }
                            
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"Graph API attack failed: {e}")
        
        return {'success': False}
    
    def method_cdn_bruteforce(self, video_id):
        """CDN endpoint brute force"""
        try:
            cdn_patterns = [
                f"https://scontent.xx.fbcdn.net/v/t42.9040-2/{video_id}_n.mp4",
                f"https://video.xx.fbcdn.net/v/t42.9040-2/{video_id}_n.mp4",
                f"https://scontent-hkg3-1.xx.fbcdn.net/v/t42.9040-2/{video_id}_n.mp4"
            ]
            
            for cdn_url in cdn_patterns:
                try:
                    response = self.session.head(cdn_url, timeout=10)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '')
                        if 'video' in content_type:
                            return {
                                'success': True,
                                'method': 'cdn-bruteforce',
                                'video_url': cdn_url
                            }
                            
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"CDN brute force failed: {e}")
        
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
                '--sub-lang', 'vi,en', '--skip-download',
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
                            'title': 'Facebook Video',
                            'transcript': content,
                            'source': 'facebook_yt-dlp_subs',
                            'language': 'auto'
                        }
        except Exception:
            pass
        return None

    def _resolve_share_url(self, url):
        """Resolve /share/v/ short links to their canonical URL."""
        if '/share/v/' in url:
            try:
                resp = requests.get(url, allow_redirects=True, timeout=10,
                                    headers={'User-Agent': 'curl/8.0'})
                resolved = resp.url.split('?')[0]
                if resolved != url:
                    print(f"📎 Resolved share URL → {resolved}")
                    return resolved
            except Exception:
                pass
        return url

    def extract_facebook_direct(self, url):
        """Main extraction method"""
        url = self._resolve_share_url(url)
        print(f"🚀 Facebook Direct Attack: {url}")

        # --- Subtitle-first: fast path ---
        sub_result = self._check_subtitles(url)
        if sub_result:
            print("✅ Subtitles found — skipping heavy extraction")
            return sub_result

        video_id = self._extract_video_id(url)
        if not video_id:
            return {'success': False, 'error': 'Could not extract video ID'}

        print(f"🎯 Video ID: {video_id}")

        # Try all attack methods
        methods = [
            lambda: self.method_mobile_webapp_extraction(video_id),
            lambda: self.method_graph_api_attack(video_id),
            lambda: self.method_cdn_bruteforce(video_id)
        ]
        
        successful_method = None
        
        for i, method in enumerate(methods, 1):
            method_name = method.__code__.co_name.replace('method_', '')
            print(f"\n🔥 Attack {i}: {method_name}")
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
            # Last resort: use yt-dlp to download audio + Whisper transcription
            print("\n🔄 All direct attacks blocked — trying yt-dlp audio fallback...")
            try:
                audio_file = os.path.join(self.temp_dir, f"fb_audio_{int(time.time())}.wav")
                cmd = [
                    'yt-dlp', '--js-runtimes', 'node',
                    '--remote-components', 'ejs:github',
                    '--extract-audio', '--audio-format', 'wav',
                    '--postprocessor-args', 'ffmpeg:-ar 16000 -ac 1',
                    '--output', audio_file.replace('.wav', '.%(ext)s'),
                    url
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    # Find the output file — check expected name, then scan dir
                    found = None
                    for ext in ['wav', 'mp3', 'm4a', 'webm']:
                        candidate = audio_file.replace('.wav', f'.{ext}')
                        if os.path.exists(candidate):
                            found = candidate
                            break
                    if not found:
                        for f in os.listdir(self.temp_dir):
                            if f.endswith(('.wav', '.mp3', '.m4a', '.webm')):
                                found = os.path.join(self.temp_dir, f)
                                break
                    audio_file = found
                    if audio_file and os.path.exists(audio_file):
                        transcript = self._transcribe_audio(audio_file)
                        os.remove(audio_file)
                        if transcript and len(transcript.strip()) > 20:
                            print(f"🎉 yt-dlp fallback SUCCESS! {len(transcript)} chars")
                            return {
                                'success': True,
                                'title': 'Facebook Video',
                                'transcript': transcript,
                                'source': 'facebook_ytdlp_whisper',
                                'language': 'auto'
                            }
            except Exception as e:
                print(f"❌ yt-dlp fallback failed: {e}")
            return {'success': False, 'error': 'ALL ATTACKS BLOCKED BY FACEBOOK'}
        
        # Process results
        title = successful_method.get('title', 'Facebook Video')
        video_urls = []
        
        if 'video_urls' in successful_method:
            video_urls = successful_method['video_urls']
        elif 'video_url' in successful_method:
            video_urls = [successful_method['video_url']]
        elif 'data' in successful_method and 'source' in successful_method['data']:
            video_urls = [successful_method['data']['source']]
        
        print(f"📝 Title: {title}")
        print(f"🎬 Video URLs found: {len(video_urls)}")
        
        # Attempt transcription
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
                        print(f"🎉 TRANSCRIPTION SUCCESS!")
                        break
                    else:
                        print(f"⚠️ Transcript too short: {len(transcript) if transcript else 0} chars")
                else:
                    print(f"❌ Audio extraction failed")
                    
            except Exception as e:
                print(f"❌ Processing error: {e}")
                continue
        
        # Final result
        result = {
            'success': True,
            'title': title,
            'video_id': video_id,
            'method': f"facebook-direct-{successful_method['method']}",
            'video_urls_found': len(video_urls)
        }
        
        if transcript:
            result['transcript'] = transcript
            result['source'] = 'facebook_direct_whisper_SUCCESS'
            result['successful_video_url'] = successful_video_url[:60] + '...'
            result['language'] = 'auto'
            print(f"\n🏆 VICTORY! Got {len(transcript)} char transcript!")
        else:
            result['transcript'] = f"Facebook Video: {title} (Found {len(video_urls)} video URLs but transcription blocked)"
            result['source'] = 'facebook_direct_metadata'
            print(f"\n⚠️ PARTIAL: Found URLs but transcription blocked")
        
        return result
    
    def _download_and_extract_audio(self, video_url):
        """Download and extract audio"""
        try:
            audio_file = os.path.join(self.temp_dir, f"audio_{int(time.time())}.mp3")
            
            # yt-dlp attempt
            cmd = [
                'yt-dlp',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--user-agent', random.choice(self.user_agents),
                '--add-header', 'Referer: https://m.facebook.com/',
                '--no-check-certificate',
                '--output', audio_file.replace('.mp3', '.%(ext)s'),
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                for ext in ['mp3', 'wav', 'm4a']:
                    test_file = audio_file.replace('.mp3', f'.{ext}')
                    if os.path.exists(test_file):
                        print(f"✅ yt-dlp success: {test_file}")
                        return test_file
            
            # Direct download attempt
            print("🔄 Trying direct download...")
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://m.facebook.com/',
                'Accept': '*/*'
            }
            
            video_file = audio_file.replace('.mp3', '.mp4')
            
            response = self.session.get(video_url, headers=headers, stream=True, timeout=30)
            if response.status_code in [200, 206]:
                with open(video_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Extract audio with ffmpeg
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-i', video_file,
                    '-vn', '-acodec', 'mp3', '-ar', '16000', '-ac', '1', '-y',
                    audio_file
                ]
                
                ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=30)
                
                if os.path.exists(video_file):
                    os.remove(video_file)
                
                if ffmpeg_result.returncode == 0 and os.path.exists(audio_file):
                    print(f"✅ Direct download success: {audio_file}")
                    return audio_file
            
        except Exception as e:
            print(f"❌ Download failed: {e}")
        
        return None
    
    def _transcribe_audio(self, audio_file):
        """Transcribe with Whisper"""
        whisper = self._get_whisper()
        if not whisper:
            return None

        try:
            print(f"🎤 Transcribing: {audio_file}")
            result = whisper.transcribe(audio_file, language="vi")
            transcript = result["text"].strip()
            
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            return transcript
            
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
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
        print("Usage: python3 facebook_direct_fixed.py <facebook_url>")
        sys.exit(1)
    
    url = sys.argv[1]
    extractor = FacebookDirectAttack()
    
    try:
        result = extractor.extract_facebook_direct(url)
        
        if result['success']:
            print(f"\n🎉 FACEBOOK BREAKTHROUGH!")
            print(f"📱 Platform: FACEBOOK")
            print(f"🎬 Title: {result['title']}")
            print(f"📝 Source: {result['source']}")
            print(f"📄 Length: {len(result['transcript'])} chars")
            
            preview = result['transcript'][:300] + "..." if len(result['transcript']) > 300 else result['transcript']
            print(f"\n📋 TRANSCRIPT:")
            print(f"\"{preview}\"")
            
            filename = f"transcript_facebook_breakthrough_{int(time.time())}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result['transcript'])
            print(f"\n💾 Saved: {filename}")
            
        else:
            print(f"\n❌ FACEBOOK DEFENSE TOO STRONG: {result.get('error')}")
    
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    main()
