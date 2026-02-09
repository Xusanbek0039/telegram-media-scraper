"""Multi-source music search engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .youtube_music import search_youtube_music
from .spotify import search_spotify_tracks
from .lyrics import search_lyrics_fallback


@dataclass
class MultiSearchResult:
    youtube: List[Dict]
    spotify: List[Dict]
    lyrics: List[Dict]


def multi_search_text(query: str) -> MultiSearchResult:
    """
    Flow (as requested):
    1) YouTube Music (YouTube-biased search)
    2) Spotify (optional)
    3) Lyrics fallback
    """
    yt = search_youtube_music(query, limit=10)
    sp = search_spotify_tracks(query, limit=5)

    ly: List[Dict] = []
    if not yt and not sp:
        ly = search_lyrics_fallback(query, limit=10)

    return MultiSearchResult(youtube=yt, spotify=sp, lyrics=ly)

