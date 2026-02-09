"""Spotify search (optional).

Requires env vars:
- SPOTIFY_CLIENT_ID
- SPOTIFY_CLIENT_SECRET
"""

from __future__ import annotations

import base64
import os
import time
from typing import Dict, List, Optional

import requests


_token_cache: Dict[str, object] = {
    "access_token": None,
    "expires_at": 0,
}


def _get_credentials() -> Optional[tuple[str, str]]:
    cid = (os.getenv("SPOTIFY_CLIENT_ID") or "").strip()
    sec = (os.getenv("SPOTIFY_CLIENT_SECRET") or "").strip()
    if not cid or not sec:
        return None
    return cid, sec


def _get_access_token() -> Optional[str]:
    creds = _get_credentials()
    if not creds:
        return None

    now = int(time.time())
    if _token_cache["access_token"] and int(_token_cache["expires_at"]) - 30 > now:
        return str(_token_cache["access_token"])

    cid, sec = creds
    basic = base64.b64encode(f"{cid}:{sec}".encode("utf-8")).decode("utf-8")

    try:
        r = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=20,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        token = data.get("access_token")
        expires_in = int(data.get("expires_in", 0) or 0)
        if not token:
            return None
        _token_cache["access_token"] = token
        _token_cache["expires_at"] = now + expires_in
        return str(token)
    except Exception:
        return None


def search_spotify_tracks(query: str, limit: int = 5, market: str = "UZ") -> List[Dict]:
    """Search Spotify tracks; returns list of {title, artist, url, album}."""
    query = (query or "").strip()
    if not query:
        return []

    token = _get_access_token()
    if not token:
        return []

    try:
        r = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "limit": limit, "market": market},
            timeout=20,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        items = (((data.get("tracks") or {}).get("items")) or [])
        out: List[Dict] = []
        for t in items:
            artists = t.get("artists") or []
            artist = artists[0].get("name") if artists else ""
            out.append(
                {
                    "title": t.get("name", ""),
                    "artist": artist,
                    "album": ((t.get("album") or {}).get("name")) or "",
                    "url": ((t.get("external_urls") or {}).get("spotify")) or "",
                }
            )
        return out
    except Exception:
        return []

