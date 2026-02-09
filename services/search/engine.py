"""Multi-source music search engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

from .youtube_music import search_youtube_music
from .spotify import search_spotify_tracks
from .lyrics import search_lyrics_fallback

logger = logging.getLogger(__name__)


@dataclass
class MultiSearchResult:
    youtube: List[Dict] = field(default_factory=list)
    spotify: List[Dict] = field(default_factory=list)
    lyrics: List[Dict] = field(default_factory=list)


def multi_search_text(query: str) -> MultiSearchResult:
    """
    Flow:
    1) YouTube Music search
    2) Spotify (optional)
    3) Lyrics fallback (only if 1+2 empty)
    """
    yt: List[Dict] = []
    sp: List[Dict] = []
    ly: List[Dict] = []

    try:
        yt = search_youtube_music(query, limit=10)
    except Exception as e:
        logger.error("YouTube search error: %s", e)

    try:
        sp = search_spotify_tracks(query, limit=5)
    except Exception as e:
        logger.error("Spotify search error: %s", e)

    if not yt and not sp:
        try:
            ly = search_lyrics_fallback(query, limit=10)
        except Exception as e:
            logger.error("Lyrics search error: %s", e)

    return MultiSearchResult(youtube=yt, spotify=sp, lyrics=ly)
