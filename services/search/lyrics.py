"""Lyrics fallback search via YouTube."""

from __future__ import annotations

import logging
from typing import Dict, List

import yt_dlp

from services.downloaders.ytdl_utils import get_ydl_base_opts

logger = logging.getLogger(__name__)


def search_lyrics_fallback(query: str, limit: int = 5) -> List[Dict]:
    query = (query or "").strip()
    if not query:
        return []

    base_opts = get_ydl_base_opts()
    ydl_opts = {
        **base_opts,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "ignoreerrors": True,
    }

    out: List[Dict] = []
    search_term = f"ytsearch{limit}:{query} lyrics"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_term, download=False)
            if not result:
                return []
            entries = result.get("entries") or []
            for entry in entries:
                if not entry:
                    continue
                vid = entry.get("id", "")
                if not vid:
                    continue
                out.append({
                    "id": vid,
                    "title": entry.get("title") or "Noma'lum",
                    "duration": entry.get("duration") or 0,
                    "url": entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
                })
    except Exception as e:
        logger.warning("Lyrics search failed for %r: %s", query, e)

    return out
