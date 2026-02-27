#!/usr/bin/env python3
"""
Setup script for Video Transcript Tool
"""

from setuptools import setup, find_packages

setup(
    name="video-transcript-tool",
    version="1.0.0",
    description="🎬 Extract transcripts from YouTube, TikTok, Facebook videos using Whisper AI",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Trần Việt Anh",
    author_email="viettran1502@gmail.com",
    maintainer="Trần Việt Anh", 
    maintainer_email="viettran1502@gmail.com",
    contributors=[
        "Cot.ghw@gmail.com"
    ],
    url="https://github.com/viettran1502/video-transcript-tool",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "whisper @ git+https://github.com/openai/whisper.git",
        "yt-dlp>=2023.12.30", 
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "ffmpeg-python>=0.2.0",
        "pydub>=0.25.0",
        "selenium>=4.15.0",
        "undetected-chromedriver>=3.5.0",
        "typing-extensions>=4.8.0",
        "tqdm>=4.66.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "transcript-extractor=transcript_extractor:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords=[
        "transcript", "video", "whisper", "ai", "youtube", "tiktok", 
        "speech-to-text", "automation", "python"
    ],
    project_urls={
        "Bug Reports": "https://github.com/viettran1502/video-transcript-tool/issues",
        "Source": "https://github.com/viettran1502/video-transcript-tool",
        "Funding": "https://github.com/sponsors/viettran1502",
    },
)
