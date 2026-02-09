"""Shazam audio recognition service (works without ffmpeg)"""
import logging
import os
from typing import Optional, Dict

from shazamio import Shazam, HTTPClient
from aiohttp_retry import ExponentialRetry

logger = logging.getLogger(__name__)

HAS_PYDUB = False
try:
    from pydub import AudioSegment
    import tempfile
    _test = AudioSegment.silent(duration=100)
    HAS_PYDUB = True
except Exception:
    pass


class ShazamService:
    def __init__(self):
        self._shazam = None

    def _get_shazam(self) -> Shazam:
        if self._shazam is None:
            self._shazam = Shazam(
                http_client=HTTPClient(
                    retry_options=ExponentialRetry(
                        attempts=5,
                        max_timeout=60.0,
                        statuses={500, 502, 503, 504, 429},
                    ),
                ),
            )
        return self._shazam

    def _prepare_snippet(self, file_path: str) -> Optional[bytes]:
        """Audio faylni bytes ga aylantiradi. ffmpeg bo'lsa snippet kesadi, bo'lmasa raw bytes."""
        if not os.path.exists(file_path):
            return None

        if HAS_PYDUB:
            try:
                audio = AudioSegment.from_file(file_path)
                duration_ms = len(audio)
                target_ms = 12_000

                if duration_ms > target_ms:
                    start = max((duration_ms - target_ms) // 2, 0)
                    audio = audio[start:start + target_ms]

                audio = audio.set_channels(1).set_frame_rate(44_100).set_sample_width(2)

                tmp_dir = tempfile.gettempdir()
                out_path = os.path.join(tmp_dir, f"shazam_{os.getpid()}.wav")
                audio.export(out_path, format="wav")
                with open(out_path, "rb") as f:
                    data = f.read()
                try:
                    os.remove(out_path)
                except OSError:
                    pass
                return data
            except Exception as e:
                logger.warning("pydub snippet failed, using raw bytes: %s", e)

        with open(file_path, "rb") as f:
            return f.read()

    async def recognize(self, file_path: str) -> Optional[Dict]:
        if not os.path.exists(file_path):
            return {
                "is_successful": False,
                "error_message": "Fayl topilmadi.",
            }

        audio_bytes = self._prepare_snippet(file_path)
        if not audio_bytes:
            return {
                "is_successful": False,
                "error_message": "Audio o'qib bo'lmadi.",
            }

        try:
            shazam = self._get_shazam()
            result = await shazam.recognize(audio_bytes)

            track = result.get("track") if isinstance(result, dict) else None

            if not track:
                return {
                    "is_successful": False,
                    "error_message": "Shazam qo'shiqni topa olmadi. Boshqa audio yuboring.",
                }

            album = ""
            try:
                sections = track.get("sections", [])
                if sections:
                    metadata = sections[0].get("metadata", [])
                    if metadata:
                        album = metadata[0].get("text", "")
            except Exception:
                pass

            return {
                "title": track.get("title", "Noma'lum"),
                "artist": track.get("subtitle", "Noma'lum"),
                "album": album,
                "genre": track.get("genres", {}).get("primary", ""),
                "shazam_url": track.get("url", ""),
                "cover": track.get("images", {}).get("coverarthq", "")
                         or track.get("images", {}).get("coverart", ""),
                "is_successful": True,
            }
        except Exception as e:
            logger.error("Shazam recognize error: %s", e)
            return {
                "is_successful": False,
                "error_message": f"Shazam xatolik: {e}",
            }
