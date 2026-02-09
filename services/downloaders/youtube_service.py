"""YouTube downloader service"""
import os
import yt_dlp
from typing import Optional, Dict, List
from .base import BaseDownloader
from .ytdl_utils import get_ydl_base_opts

VIDEO_QUALITIES = ['144', '240', '360', '480', '720', '1080']


class YouTubeService(BaseDownloader):
    """YouTube platform downloader"""

    def detect(self, url: str) -> bool:
        import re
        pattern = re.compile(
            r'(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w\-]+'
        )
        return bool(pattern.search(url))

    def get_info(self, url: str) -> Optional[Dict]:
        ydl_opts = get_ydl_base_opts()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Video'),
                    'channel': info.get('channel', info.get('uploader', '')),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'formats': info.get('formats', []),
                    'url': url,
                    'id': info.get('id', 'video'),
                }
        except Exception:
            return None

    def get_available_qualities(self, url: str) -> List[Dict]:
        info = self.get_info(url)
        if not info:
            return []

        formats = info.get('formats', [])
        available = []
        seen = set()

        for f in formats:
            height = f.get('height')
            if not height or f.get('vcodec') == 'none':
                continue
            label = str(height)
            if label not in seen and label in VIDEO_QUALITIES:
                filesize = f.get('filesize') or f.get('filesize_approx') or 0
                seen.add(label)
                available.append({
                    'label': f'{label}p',
                    'height': label,
                    'filesize': filesize
                })

        available.sort(key=lambda x: int(x['height']))

        # Audio option
        audio_size = 0
        for f in formats:
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                audio_size = f.get('filesize') or f.get('filesize_approx') or 0
                break
        available.append({
            'label': 'Audio',
            'height': 'audio',
            'filesize': audio_size
        })

        return available

    def download_video(self, url: str, output_path: str, quality: Optional[str] = None) -> Optional[str]:
        video_id = url.split('v=')[-1].split('&')[0] if 'v=' in url else 'video'
        base = get_ydl_base_opts()
        if quality and quality != 'audio':
            ydl_opts = {
                **base,
                'format': f'best[height<={quality}][ext=mp4]/best[height<={quality}]/best',
                'outtmpl': output_path.replace('.mp4', '.%(ext)s'),
                'merge_output_format': 'mp4',
            }
        else:
            ydl_opts = {
                **base,
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path.replace('.mp4', '.%(ext)s'),
                'merge_output_format': 'mp4',
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Check if file exists with different extensions
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

            # Check if file exists with different extensions
            for ext in ['mp3', 'm4a', 'ogg']:
                alt_path = output_path.replace('.mp3', f'.{ext}')
                if os.path.exists(alt_path):
                    return alt_path
            return None
        except Exception:
            return None
