"""Base downloader interface"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, List


class BaseDownloader(ABC):
    """Base class for all platform downloaders"""

    @abstractmethod
    def detect(self, url: str) -> bool:
        """Check if URL belongs to this platform"""
        pass

    @abstractmethod
    def get_info(self, url: str) -> Optional[Dict]:
        """Get video information without downloading"""
        pass

    @abstractmethod
    def download_video(self, url: str, output_path: str, quality: Optional[str] = None) -> Optional[str]:
        """Download video file"""
        pass

    @abstractmethod
    def download_audio(self, url: str, output_path: str) -> Optional[str]:
        """Download audio file"""
        pass

    @abstractmethod
    def get_available_qualities(self, url: str) -> List[Dict]:
        """Get available quality options"""
        pass
