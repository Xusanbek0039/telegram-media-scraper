"""Shazam audio recognition service (improved)"""
import os
import tempfile
from typing import Optional, Dict

from shazamio import Shazam
from pydub import AudioSegment


class ShazamService:
    """
    Shazam audio recognition service.

    Yaxshilangan yondashuv:
    - Har xil formatdagi fayllarni (ogg, mp3, mp4, m4a, webm, ...) avtomatik o'qiydi
    - Faqat 8–12 soniyalik audio bo'lagini ajratib oladi (Shazam uchun ideal)
    - Mono, 44.1 kHz, 16-bit wav formatiga konvert qiladi
    """

    def __init__(self):
        self.shazam = Shazam()

    def _prepare_snippet(self, file_path: str) -> Optional[str]:
        """
        Kiruvchi audio/video fayldan qisqa audio bo'lak (snippet) tayyorlash.

        Shazam odatda 5–15 soniya oralig'idagi, sifatli audio bilan eng yaxshi ishlaydi.
        """
        if not os.path.exists(file_path):
            return None

        try:
            # Pydub orqali har qanday formatni o'qish (ffmpeg talab qilinadi)
            audio = AudioSegment.from_file(file_path)

            # Juda qisqa bo'lsa ham ishlayveradi, lekin 8–12 soniya oralig'ini olishga harakat qilamiz
            duration_ms = len(audio)
            target_ms = 10_000  # 10 soniya

            if duration_ms <= target_ms:
                snippet = audio
            else:
                # O'rtasidan 10 soniya kesib olamiz — ko'p hollarda qo'shiqning asosiy qismi
                start = max((duration_ms - target_ms) // 2, 0)
                end = start + target_ms
                snippet = audio[start:end]

            # Mono, 44.1 kHz, 16-bit PCM — Shazam uchun standart
            snippet = snippet.set_channels(1).set_frame_rate(44_100).set_sample_width(2)

            # Vaqtinchalik wav faylga saqlaymiz
            tmp_dir = tempfile.gettempdir()
            out_path = os.path.join(tmp_dir, f"shazam_snippet_{os.path.basename(file_path)}.wav")
            snippet.export(out_path, format="wav")
            return out_path
        except Exception:
            # Agar konvert qilishda xatolik bo'lsa, to'g'ridan-to'g'ri original faylni ishlatib ko'ramiz
            return file_path

    async def recognize(self, file_path: str) -> Optional[Dict]:
        """
        Recognize audio file using Shazam.

        Args:
            file_path: Original file path (voice, audio, video)

        Returns:
            Dict with recognition results or None if failed
        """
        if not os.path.exists(file_path):
            return None

        snippet_path = self._prepare_snippet(file_path)
        if not snippet_path or not os.path.exists(snippet_path):
            return {
                "is_successful": False,
                "error_message": "Audio snippet tayyorlab bo'lmadi. ffmpeg o'rnatilganligini tekshiring.",
            }

        try:
            # ShazamIO ning hozirgi API'si: recognize(file_path)
            result = await self.shazam.recognize(snippet_path)
            track = result.get("track")

            if not track:
                return {
                    "is_successful": False,
                    "error_message": "Shazam hech qanday qo'shiq topmadi.",
                }

            return {
                "title": track.get("title", "Noma'lum"),
                "artist": track.get("subtitle", "Noma'lum"),
                "album": (
                    track.get("sections", [{}])[0]
                    .get("metadata", [{}])[0]
                    .get("text", "")
                    if track.get("sections")
                    else ""
                ),
                "genre": track.get("genres", {}).get("primary", ""),
                "shazam_url": track.get("url", ""),
                "cover": track.get("images", {}).get("coverarthq", ""),
                "lyrics": "",  # Keyinchalik kengaytirish mumkin
                "is_successful": True,
            }
        except Exception as e:
            return {
                "is_successful": False,
                "error_message": str(e),
            }
        finally:
            # Vaqtinchalik snippet faylini tozalaymiz
            if snippet_path and snippet_path != file_path:
                try:
                    os.remove(snippet_path)
                except OSError:
                    pass
