"""Shazam audio recognition service"""
import os
from typing import Optional, Dict
from shazamio import Shazam


class ShazamService:
    """Shazam audio recognition service"""

    def __init__(self):
        self.shazam = Shazam()

    async def recognize(self, file_path: str) -> Optional[Dict]:
        """
        Recognize audio file using Shazam
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dict with recognition results or None if failed
        """
        if not os.path.exists(file_path):
            return None

        try:
            result = await self.shazam.recognize(file_path)
            track = result.get('track')
            
            if not track:
                return None

            return {
                'title': track.get('title', 'Noma\'lum'),
                'artist': track.get('subtitle', 'Noma\'lum'),
                'album': (
                    track.get('sections', [{}])[0].get('metadata', [{}])[0].get('text', '')
                    if track.get('sections') else ''
                ),
                'genre': track.get('genres', {}).get('primary', ''),
                'shazam_url': track.get('url', ''),
                'cover': track.get('images', {}).get('coverarthq', ''),
                'lyrics': '',  # Can be extended later
                'is_successful': True,
            }
        except Exception as e:
            return {
                'is_successful': False,
                'error_message': str(e),
            }
