"""Shared yt-dlp options with ffmpeg support"""
import os
from django.conf import settings

# .env dan FFMPEG_PATH yoki FFPROBE_PATH o'qish
FFMPEG_PATH = os.getenv('FFMPEG_PATH', '')
FFPROBE_PATH = os.getenv('FFPROBE_PATH', '')


def get_ydl_base_opts():
    """yt-dlp uchun asosiy opts — ffmpeg_path bilan"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    if FFMPEG_PATH and os.path.isfile(FFMPEG_PATH):
        opts['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)
    elif FFPROBE_PATH and os.path.isfile(FFPROBE_PATH):
        opts['ffmpeg_location'] = os.path.dirname(FFPROBE_PATH)
    return opts
