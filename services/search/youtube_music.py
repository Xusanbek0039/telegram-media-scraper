"""YouTube Music-ish search (implemented via YouTube search).

Without official YouTube Music API keys, we bias queries to return music tracks.
"""

from __future__ import annotations

from typing import Dict, List

import yt_dlp


def search_youtube_music(query: str, limit: int = 10) -> List[Dict]:
    """
    Returns a list of YouTube results shaped like:
    {id, title, duration, url}
    """
    query = (query or "").strip()
    if not query:
        return []

    # query variations to bias towards songs
    candidates = [
        query,
        f"{query} audio",
        f"{query} topic",
        f"{query} official audio",
    ]

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": f"ytsearch{limit}",
    }

    seen = set()
    out: List[Dict] = []

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for q in candidates:
            try:
                result = ydl.extract_info(q, download=False)
                entries = result.get("entries", []) if isinstance(result, dict) else []
                for entry in entries:
                    if not entry:
                        continue
                    vid = entry.get("id", "")
                    if not vid or vid in seen:
                        continue
                    seen.add(vid)
                    out.append(
                        {
                            "id": vid,
                            "title": entry.get("title", "Noma'lum"),
                            "duration": entry.get("duration", 0),
                            "url": f"https://www.youtube.com/watch?v={vid}",
                        }
                    )
                    if len(out) >= limit:
                        return out
            except Exception:
                continue

    return out

