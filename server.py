#!/usr/bin/env python3
"""
Backend Service for Video Transcript Tool.

Loads Whisper once at startup, keeps it in memory, and caches results so
repeat URLs return instantly.  All extractors share the singleton model
via whisper_manager.

Usage:
    python3 server.py                          # defaults
    WHISPER_MODEL=large-v3 PORT=8080 python3 server.py
"""

import os
import time
import uuid
import threading
import logging
from urllib.parse import urlparse

from flask import Flask, request, jsonify
from flask_cors import CORS

from whisper_manager import preload_model
from transcript_extractor import WhisperTranscriptExtractor
from facebook_direct_fixed import FacebookDirectAttack
from douyin_breakthrough import DouyinBreakthrough

# ---------------------------------------------------------------------------
# Configuration (env vars)
# ---------------------------------------------------------------------------
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")
PORT = int(os.environ.get("PORT", "5000"))
CACHE_TTL = int(os.environ.get("CACHE_TTL", "3600"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("server")

# ---------------------------------------------------------------------------
# App + CORS
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# Startup: load model + create extractors once
# ---------------------------------------------------------------------------
logger.info("Pre-loading Whisper model '%s' …", WHISPER_MODEL)
preload_model(WHISPER_MODEL)

_startup_time = time.time()

extractor_yt = WhisperTranscriptExtractor(whisper_model=WHISPER_MODEL)
extractor_fb = FacebookDirectAttack(whisper_model=WHISPER_MODEL)
extractor_dy = DouyinBreakthrough(whisper_model=WHISPER_MODEL)

# ---------------------------------------------------------------------------
# Transcription lock — serializes extraction (temp-dir collisions, CPU-bound)
# ---------------------------------------------------------------------------
_transcription_lock = threading.Lock()

# ---------------------------------------------------------------------------
# In-memory cache  {normalized_url: (timestamp, response_dict)}
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()


def _normalize_url(url: str) -> str:
    """Strip trailing slashes and fragments for cache key."""
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl().rstrip("/")


def _cache_get(url: str) -> dict | None:
    key = _normalize_url(url)
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        ts, data = entry
        if time.time() - ts > CACHE_TTL:
            del _cache[key]
            return None
        return data


def _cache_put(url: str, data: dict) -> None:
    key = _normalize_url(url)
    with _cache_lock:
        _cache[key] = (time.time(), data)


# ---------------------------------------------------------------------------
# Async jobs  {job_id: {"status", "result", "created_at"}}
# ---------------------------------------------------------------------------
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Core transcription logic
# ---------------------------------------------------------------------------


def _identify_platform(url: str) -> str:
    """Determine platform from URL (mirrors extractor_yt.identify_platform)."""
    return extractor_yt.identify_platform(url)


def _do_transcribe(url: str, language: str | None = None) -> dict:
    """Run transcription; returns a response dict.  Caller must hold no locks."""
    # Expand shortened URLs (vt.tiktok.com, vm.tiktok.com, etc.)
    url = extractor_yt.expand_shortened_url(url)

    # Check cache first
    cached = _cache_get(url)
    if cached is not None:
        return {**cached, "cached": True}

    platform = _identify_platform(url)

    start = time.time()
    with _transcription_lock:
        # Double-check cache after acquiring lock (another thread may have
        # populated it while we waited).
        cached = _cache_get(url)
        if cached is not None:
            return {**cached, "cached": True}

        if platform == "youtube":
            result = extractor_yt.extract_youtube(url)
        elif platform == "tiktok":
            result = extractor_yt.extract_tiktok(url)
        elif platform == "facebook":
            result = extractor_yt.extract_facebook(url)
        elif platform == "douyin":
            result = extractor_dy.extract_douyin_breakthrough(url)
        else:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}",
                "cached": False,
                "processing_time_seconds": round(time.time() - start, 2),
            }

    elapsed = round(time.time() - start, 2)

    if "error" in result:
        return {
            "success": False,
            "error": result["error"],
            "platform": platform,
            "cached": False,
            "processing_time_seconds": elapsed,
        }

    response = {
        "success": True,
        "title": result.get("title", ""),
        "transcript": result.get("transcript", ""),
        "source": result.get("source", ""),
        "language": language or result.get("language", "auto"),
        "platform": platform,
        "cached": False,
        "processing_time_seconds": elapsed,
    }

    _cache_put(url, response)
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.route("/api/health", methods=["GET"])
def health():
    with _cache_lock:
        cache_size = len(_cache)
    with _jobs_lock:
        active = sum(1 for j in _jobs.values() if j["status"] == "processing")
    return jsonify({
        "status": "ok",
        "model": WHISPER_MODEL,
        "uptime_seconds": round(time.time() - _startup_time, 1),
        "cache_size": cache_size,
        "active_jobs": active,
    })


@app.route("/api/transcribe", methods=["POST"])
def transcribe_sync():
    body = request.get_json(silent=True) or {}
    url = body.get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "Missing 'url' field"}), 400

    language = body.get("language")
    result = _do_transcribe(url, language)
    status_code = 200 if result.get("success") else 502
    return jsonify(result), status_code


@app.route("/api/transcribe/async", methods=["POST"])
def transcribe_async():
    body = request.get_json(silent=True) or {}
    url = body.get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "Missing 'url' field"}), 400

    language = body.get("language")
    job_id = uuid.uuid4().hex[:12]

    with _jobs_lock:
        _jobs[job_id] = {
            "status": "processing",
            "result": None,
            "created_at": time.time(),
        }

    def _run():
        result = _do_transcribe(url, language)
        with _jobs_lock:
            _jobs[job_id]["status"] = "completed"
            _jobs[job_id]["result"] = result

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "status": "processing"}), 202


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "processing":
        return jsonify({"job_id": job_id, "status": "processing"}), 200
    return jsonify({"job_id": job_id, "status": "completed", **job["result"]}), 200


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting server on port %d (model=%s, cache_ttl=%ds)",
                PORT, WHISPER_MODEL, CACHE_TTL)
    app.run(host="0.0.0.0", port=PORT, debug=False)
