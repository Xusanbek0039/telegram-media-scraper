"""Shazam audio recognition service (improved for shazamio 0.8+)"""
import logging
import os
import tempfile
from typing import Optional, Dict

from shazamio import Shazam, Serialize, HTTPClient
from aiohttp_retry import ExponentialRetry
from pydub import AudioSegment

logger = logging.getLogger(__name__)


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

    def _prepare_snippet(self, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            return None

        try:
            audio = AudioSegment.from_file(file_path)

            duration_ms = len(audio)
            target_ms = 12_000

            if duration_ms <= target_ms:
                snippet = audio
            else:
                start = max((duration_ms - target_ms) // 2, 0)
                end = start + target_ms
                snippet = audio[start:end]

            snippet = snippet.set_channels(1).set_frame_rate(44_100).set_sample_width(2)

            tmp_dir = tempfile.gettempdir()
            out_path = os.path.join(tmp_dir, f"shazam_snippet_{os.getpid()}_{os.path.basename(file_path)}.wav")
            snippet.export(out_path, format="wav")
            return out_path
        except Exception as e:
            logger.warning("Snippet prepare error: %s", e)
            return file_path

    async def recognize(self, file_path: str) -> Optional[Dict]:
        if not os.path.exists(file_path):
            return {
                "is_successful": False,
                "error_message": "Fayl topilmadi.",
            }

        snippet_path = self._prepare_snippet(file_path)
        if not snippet_path or not os.path.exists(snippet_path):
            return {
                "is_successful": False,
                "error_message": "Audio snippet tayyorlab bo'lmadi. ffmpeg o'rnatilganligini tekshiring.",
            }

        try:
            shazam = self._get_shazam()

            with open(snippet_path, "rb") as f:
                audio_bytes = f.read()

            result = await shazam.recognize(audio_bytes)

            track = result.get("track") if isinstance(result, dict) else None

            if not track:
                return {
                    "is_successful": False,
                    "error_message": "Shazam hech qanday qo'shiq topmadi. Boshqa audio yuboring.",
                }

            album = ""
            try:
                sections = track.get("sections", [])
                if sections and len(sections) > 0:
                    metadata = sections[0].get("metadata", [])
                    if metadata and len(metadata) > 0:
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
        finally:
            if snippet_path and snippet_path != file_path:
                try:
                    os.remove(snippet_path)
                except OSError:
                    pass
