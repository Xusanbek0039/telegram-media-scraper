"""YouTube Music search via yt-dlp.

Searches YouTube with music-biased queries and returns track info.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import yt_dlp

from services.downloaders.ytdl_utils import get_ydl_base_opts

logger = logging.getLogger(__name__)


def search_youtube_music(query: str, limit: int = 10) -> List[Dict]:
    """
    Returns a list of YouTube results:
    {id, title, duration, url, artist}
    """
    query = (query or "").strip()
    if not query:
        return []

    search_queries = [
        f"ytsearch{limit}:{query} audio",
        f"ytsearch{limit}:{query} official audio",
        f"ytsearch{limit}:{query}",
        f"ytsearch{limit}:{query} music",
        f"ytsearch{limit}:{query} song",
    ]

    base_opts = get_ydl_base_opts()
    ydl_opts = {
        **base_opts,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "ignoreerrors": True,
    }

    seen = set()
    out: List[Dict] = []

    for sq in search_queries:
        if len(out) >= limit:
            break
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(sq, download=False)
                if not result:
                    continue
                entries = result.get("entries") or []
                for entry in entries:
                    if not entry:
                        continue
                    vid = entry.get("id", "")
                    if not vid or vid in seen:
                        continue
                    seen.add(vid)
                    title = entry.get("title") or "Noma'lum"
                    channel = entry.get("channel") or entry.get("uploader") or ""
                    out.append({
                        "id": vid,
                        "title": title,
                        "artist": channel,
                        "duration": entry.get("duration") or 0,
                        "url": entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
                    })
                    if len(out) >= limit:
                        break
        except Exception as e:
            logger.warning("YouTube search failed for %r: %s", sq, e)
            continue

    return out
