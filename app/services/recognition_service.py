from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class RecognitionResult:
    title: str
    artist: str
    album: Optional[str] = None
    cover_url: Optional[str] = None
    source_url: Optional[str] = None
    video_url: Optional[str] = None
    preview_url: Optional[str] = None


class RecognitionService:
    """Music recognition via AudD API (legal, requires API token)."""

    API_URL = "https://api.audd.io/"

    def __init__(self, api_token: str):
        self.api_token = api_token

    @property
    def is_configured(self) -> bool:
        return bool(self.api_token and self.api_token != "your_audd_api_token_here")

    async def recognize_bytes(
        self,
        file_bytes: bytes,
        filename: str = "audio.mp3",
    ) -> Optional[RecognitionResult]:
        if not self.is_configured:
            raise RuntimeError("AUDD_API_TOKEN sozlanmagan")

        data = {
            "api_token": self.api_token,
            "return": "apple_music,spotify,deezer",
        }
        files = {"file": (filename, file_bytes)}

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(self.API_URL, data=data, files=files)
            response.raise_for_status()
            payload = response.json()

        if payload.get("status") != "success" or not payload.get("result"):
            return None

        result = payload["result"]
        title = result.get("title")
        artist = result.get("artist")
        if not title or not artist:
            return None

        album = result.get("album")
        cover_url = None
        source_url = None
        preview_url = None

        for key in ("deezer", "spotify", "apple_music"):
            provider = result.get(key) or {}
            if not isinstance(provider, dict):
                continue
            cover_url = cover_url or provider.get("image") or provider.get("artwork")
            source_url = source_url or provider.get("link") or provider.get("url")
            if not preview_url:
                preview_url = provider.get("preview")
                previews = provider.get("previews")
                if not preview_url and isinstance(previews, list) and previews:
                    preview_url = previews[0]

        song_link = result.get("song_link")
        source_url = source_url or song_link

        return RecognitionResult(
            title=title,
            artist=artist,
            album=album,
            cover_url=cover_url,
            source_url=source_url,
            preview_url=preview_url,
        )
