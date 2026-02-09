"""Lyrics fallback search.

We implement lyrics search by running a YouTube search with 'lyrics' bias.
This is used only when YouTube+Spotify didn't give solid results.
"""

from __future__ import annotations

from typing import Dict, List

import yt_dlp


def search_lyrics_fallback(query: str, limit: int = 5) -> List[Dict]:
    query = (query or "").strip()
    if not query:
        return []

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": f"ytsearch{limit}",
    }

    out: List[Dict] = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(f"{query} lyrics", download=False)
            entries = result.get("entries", []) if isinstance(result, dict) else []
            for entry in entries:
                if not entry:
                    continue
                vid = entry.get("id", "")
                if not vid:
                    continue
                out.append(
                    {
                        "id": vid,
                        "title": entry.get("title", "Noma'lum"),
                        "duration": entry.get("duration", 0),
                        "url": f"https://www.youtube.com/watch?v={vid}",
                    }
                )
            return out
        except Exception:
            return []

