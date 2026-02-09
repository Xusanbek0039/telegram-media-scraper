"""TikTok downloader service"""
import os
import yt_dlp
from typing import Optional, Dict, List
from .base import BaseDownloader
from .ytdl_utils import get_ydl_base_opts


class TikTokService(BaseDownloader):
    """TikTok platform downloader"""

    def detect(self, url: str) -> bool:
        import re
        pattern = re.compile(
            r'(https?://)?(www\.|vm\.|vt\.)?tiktok\.com/[\w\-@/.]+'
        )
        return bool(pattern.search(url))

    def get_info(self, url: str) -> Optional[Dict]:
        ydl_opts = get_ydl_base_opts()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'TikTok Video'),
                    'channel': info.get('uploader', 'TikTok'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'url': url,
                    'id': info.get('id', 'tiktok'),
                }
        except Exception:
            return None

    def get_available_qualities(self, url: str) -> List[Dict]:
        return [
            {'label': 'Video', 'height': 'best', 'filesize': 0},
            {'label': 'Audio', 'height': 'audio', 'filesize': 0}
        ]

    def download_video(self, url: str, output_path: str, quality: Optional[str] = None) -> Optional[str]:
        video_id = str(abs(hash(url)))[-10:]
        ydl_opts = {
            **get_ydl_base_opts(),
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_path.replace('.mp4', '.%(ext)s'),
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            for ext in ['mp4', 'webm', 'mkv']:
                alt_path = output_path.replace('.mp4', f'.{ext}')
                if os.path.exists(alt_path):
                    return alt_path
            return None
        except Exception:
            return None

    def download_audio(self, url: str, output_path: str) -> Optional[str]:
        ydl_opts = {
            **get_ydl_base_opts(),
            'format': 'bestaudio/best',
            'outtmpl': output_path.replace('.mp3', '.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            for ext in ['mp3', 'm4a', 'ogg']:
                alt_path = output_path.replace('.mp3', f'.{ext}')
                if os.path.exists(alt_path):
                    return alt_path
            return None
        except Exception:
            return None
