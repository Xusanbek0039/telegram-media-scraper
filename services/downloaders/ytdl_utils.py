"""Shared yt-dlp options with ffmpeg support"""
import os

# .env dan FFMPEG_PATH — ffmpeg joylashgan papka yo'li
FFMPEG_PATH = os.getenv('FFMPEG_PATH', '/home/adminmas/django-botv1/bot').strip()


def _get_ffmpeg_dir():
    """ffmpeg joylashgan papkani qaytaradi (yt-dlp ffmpeg_location uchun)"""
    if not FFMPEG_PATH:
        return '/home/adminmas/django-botv1/bot'
    if os.path.isfile(FFMPEG_PATH):
        return os.path.dirname(FFMPEG_PATH)
    if os.path.isdir(FFMPEG_PATH):
        return FFMPEG_PATH
    return '/home/adminmas/django-botv1/bot'


def get_ydl_base_opts():
    """yt-dlp uchun asosiy opts — ffmpeg_path bilan"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    ffmpeg_dir = _get_ffmpeg_dir()
    if ffmpeg_dir:
        opts['ffmpeg_location'] = ffmpeg_dir
    return opts
