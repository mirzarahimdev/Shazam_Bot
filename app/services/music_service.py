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
    """Legal catalog search via Deezer public API (no API key required)."""

    DEEZER_SEARCH = "https://api.deezer.com/search"
    ITUNES_SEARCH = "https://itunes.apple.com/search"

    def __init__(self, youtube_api_key: str = ""):
        self.youtube_api_key = youtube_api_key

    async def search(self, query: str, limit: int = 5) -> list[TrackInfo]:
        query = query.strip()
        if not query or len(query) > 200:
            return []

        tracks = await self._search_deezer(query, limit)
        if not tracks:
            tracks = await self._search_itunes(query, limit)

        for track in tracks:
            if not track.video_url:
                track.video_url = self.build_official_video_search_url(track.artist, track.title)
        return tracks

    async def _search_deezer(self, query: str, limit: int) -> list[TrackInfo]:
        params = {"q": query, "limit": limit}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.DEEZER_SEARCH, params=params)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        results: list[TrackInfo] = []
        for item in data.get("data", []):
            artist = (item.get("artist") or {}).get("name")
            album = (item.get("album") or {}).get("title")
            cover = (item.get("album") or {}).get("cover_medium")
            if not artist or not item.get("title"):
                continue
            results.append(
                TrackInfo(
                    external_id=str(item.get("id")),
                    title=item["title"],
                    artist=artist,
                    album=album,
                    cover_url=cover,
                    duration=item.get("duration"),
                    preview_url=item.get("preview"),
                    source_url=item.get("link"),
                    video_url=None,
                    provider="deezer",
                )
            )
        return results

    async def _search_itunes(self, query: str, limit: int) -> list[TrackInfo]:
        params = {
            "term": query,
            "media": "music",
            "entity": "song",
            "limit": limit,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
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

    async def find_official_video(self, artist: str, title: str) -> dict:
        """Return official video metadata. Prefer YouTube Data API; fallback to search URL."""
        search_url = self.build_official_video_search_url(artist, title)
        result = {
            "title": f"{artist} — {title} (Official Music Video)",
            "thumbnail": None,
            "duration": None,
            "url": search_url,
            "provider": "youtube_search",
        }

        if not self.youtube_api_key:
            return result

        params = {
            "part": "snippet",
            "q": f"{artist} {title} official music video",
            "type": "video",
            "maxResults": 1,
            "key": self.youtube_api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
            items = data.get("items") or []
            if not items:
                return result
            video_id = items[0]["id"]["videoId"]
            snippet = items[0]["snippet"]
            result.update(
                {
                    "title": snippet.get("title") or result["title"],
                    "thumbnail": (snippet.get("thumbnails") or {}).get("medium", {}).get("url"),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "provider": "youtube",
                }
            )
        except Exception:
            return result
        return result

    @staticmethod
    def build_official_video_search_url(artist: str, title: str) -> str:
        q = quote_plus(f"{artist} {title} official music video")
        return f"https://www.youtube.com/results?search_query={q}"

    @staticmethod
    def format_track_message(track: TrackInfo) -> str:
        return (
            f"🎵 <b>{track.title}</b>\n"
            f"👤 {track.artist}\n"
            f"💿 {track.album or '—'}\n"
            f"⏱️ {format_duration(track.duration)}\n"
            f"🔗 <a href=\"{track.source_url}\">Rasmiy manba</a>"
        )
