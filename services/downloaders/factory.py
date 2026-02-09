"""Downloader factory - detects platform and returns appropriate downloader"""
from typing import Optional
from .base import BaseDownloader
from .youtube_service import YouTubeService
from .instagram_service import InstagramService
from .tiktok_service import TikTokService
from .snapchat_service import SnapchatService
from .likee_service import LikeeService


class DownloaderFactory:
    """Factory to get appropriate downloader for URL"""

    _downloaders = [
        YouTubeService(),
        InstagramService(),
        TikTokService(),
        SnapchatService(),
        LikeeService(),
    ]

    @classmethod
    def get_downloader(cls, url: str) -> Optional[BaseDownloader]:
        """Get appropriate downloader for URL"""
        for downloader in cls._downloaders:
            if downloader.detect(url):
                return downloader
        return None

    @classmethod
    def detect_platform(cls, url: str) -> Optional[str]:
        """Detect platform name from URL"""
        downloader = cls.get_downloader(url)
        if downloader:
            if isinstance(downloader, YouTubeService):
                return 'youtube'
            elif isinstance(downloader, InstagramService):
                return 'instagram'
            elif isinstance(downloader, TikTokService):
                return 'tiktok'
            elif isinstance(downloader, SnapchatService):
                return 'snapchat'
            elif isinstance(downloader, LikeeService):
                return 'likee'
        return 'other'
