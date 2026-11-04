import asyncio
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

import httpx


@dataclass
class TrackInfo:
    external_id: str
    title: str
    artist: str
    album: Optional[str]
    cover_url: Optional[str]
    duration: Optional[int]
    preview_url: Optional[str]
    source_url: Optional[str]
    video_url: Optional[str]
    provider: str = "deezer"


def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "—"
    minutes, sec = divmod(int(seconds), 60)
    return f"{minutes}:{sec:02d}"


class MusicService:
    """Tez Deezer qidiruv: umumiy + artist top (2 so‘rov parallel)."""

    DEEZER_SEARCH = "https://api.deezer.com/search"
    DEEZER_ARTIST = "https://api.deezer.com/search/artist"
    DEEZER_ARTIST_TOP = "https://api.deezer.com/artist/{id}/top"
    ITUNES_SEARCH = "https://itunes.apple.com/search"

    def __init__(self, youtube_api_key: str = ""):
        self.youtube_api_key = youtube_api_key

    async def search(self, query: str, limit: int = 10) -> list[TrackInfo]:
        query = query.strip()
        if not query or len(query) > 200:
            return []

        # Faqat 2 parallel so‘rov — tezroq
        general, artist_top = await asyncio.gather(
            self._search_deezer(query, limit),
            self._search_artist_top(query, limit),
        )

        tracks = self._merge_tracks(query, artist_top, general, limit=limit)

        if not tracks:
            tracks = await self._search_itunes(query, limit)

        for track in tracks:
            if not track.video_url:
                track.video_url = self.build_official_video_search_url(track.artist, track.title)
        return tracks

    def _merge_tracks(
        self,
        query: str,
        *groups: list[TrackInfo],
        limit: int,
    ) -> list[TrackInfo]:
        q = query.lower().strip()
        seen: set[str] = set()
        merged: list[TrackInfo] = []

        def _key(t: TrackInfo) -> str:
            return f"{t.provider}:{t.external_id}"

        def _score(t: TrackInfo) -> tuple:
            artist_l = (t.artist or "").lower()
            title_l = (t.title or "").lower()
            return (
                0 if artist_l == q else 1,
                0 if q in artist_l else 1,
                0 if title_l == q else 1,
                0 if q in title_l else 1,
                artist_l,
                title_l,
            )

        for group in groups:
            for track in group:
                k = _key(track)
                if k in seen:
                    continue
                seen.add(k)
                merged.append(track)

        merged.sort(key=_score)
        return merged[:limit]

    async def _search_artist_top(self, query: str, limit: int) -> list[TrackInfo]:
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.get(
                    self.DEEZER_ARTIST,
                    params={"q": query, "limit": 1},
                )
                response.raise_for_status()
                artists = (response.json() or {}).get("data") or []
                if not artists:
                    return []

                artist_id = artists[0].get("id")
                if not artist_id:
                    return []

                top = await client.get(
                    self.DEEZER_ARTIST_TOP.format(id=artist_id),
                    params={"limit": limit},
                )
                top.raise_for_status()
                items = (top.json() or {}).get("data") or []
        except Exception:
            return []

        results: list[TrackInfo] = []
        for item in items:
            track = self._parse_deezer_track(item)
            if track:
                results.append(track)
        return results

    async def _search_deezer(self, query: str, limit: int) -> list[TrackInfo]:
        params = {"q": query, "limit": limit}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.get(self.DEEZER_SEARCH, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        results: list[TrackInfo] = []
        for item in data.get("data", []):
            track = self._parse_deezer_track(item)
            if track:
                results.append(track)
        return results

    @staticmethod
    def _parse_deezer_track(item: dict) -> Optional[TrackInfo]:
        artist = (item.get("artist") or {}).get("name")
        if not artist or not item.get("title"):
            return None
        album_obj = item.get("album") or {}
        cover = (
            album_obj.get("cover_xl")
            or album_obj.get("cover_big")
            or album_obj.get("cover_medium")
        )
        return TrackInfo(
            external_id=str(item.get("id")),
            title=item["title"],
            artist=artist,
            album=album_obj.get("title"),
            cover_url=cover,
            duration=item.get("duration"),
            preview_url=item.get("preview"),
            source_url=item.get("link"),
            video_url=None,
            provider="deezer",
        )

    async def _search_itunes(self, query: str, limit: int) -> list[TrackInfo]:
        params = {
            "term": query,
            "media": "music",
            "entity": "song",
            "limit": limit,
        }
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                response = await client.get(self.ITUNES_SEARCH, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        results: list[TrackInfo] = []
        for item in data.get("results", []):
            title = item.get("trackName")
            artist = item.get("artistName")
            if not title or not artist:
                continue
            duration_ms = item.get("trackTimeMillis")
            results.append(
                TrackInfo(
                    external_id=str(item.get("trackId")),
                    title=title,
                    artist=artist,
                    album=item.get("collectionName"),
                    cover_url=item.get("artworkUrl100"),
                    duration=int(duration_ms / 1000) if duration_ms else None,
                    preview_url=item.get("previewUrl"),
                    source_url=item.get("trackViewUrl"),
                    video_url=None,
                    provider="itunes",
                )
            )
        return results

    @staticmethod
    def build_official_video_search_url(artist: str, title: str) -> str:
        q = quote_plus(f"{artist} {title} official music video")
        return f"https://www.youtube.com/results?search_query={q}"
