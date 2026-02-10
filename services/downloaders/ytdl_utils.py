"""Shared yt-dlp options with ffmpeg support"""
import logging
import os

logger = logging.getLogger(__name__)

FFMPEG_DIR = '/home/adminmas/django-botv1/bot'
FFMPEG_PATH = os.getenv('FFMPEG_PATH', FFMPEG_DIR).strip()


def _get_ffmpeg_dir():
    """ffmpeg joylashgan papkani qaytaradi (yt-dlp ffmpeg_location uchun)"""
    if FFMPEG_PATH:
        if os.path.isfile(FFMPEG_PATH):
            return os.path.dirname(FFMPEG_PATH)
        if os.path.isdir(FFMPEG_PATH):
            return FFMPEG_PATH
    return FFMPEG_DIR


def get_ydl_base_opts():
    """yt-dlp uchun asosiy opts — ffmpeg_path bilan"""
    ffmpeg_dir = _get_ffmpeg_dir()
    ffmpeg_bin = os.path.join(ffmpeg_dir, 'ffmpeg')
    if os.path.isfile(ffmpeg_bin):
        logger.info("ffmpeg topildi: %s", ffmpeg_bin)
    else:
        logger.warning("ffmpeg TOPILMADI: %s — audio convert ishlamasligi mumkin", ffmpeg_bin)
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'ffmpeg_location': ffmpeg_dir,
        'prefer_ffmpeg': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        'socket_timeout': 30,
        'retries': 3,
    }
    return opts
