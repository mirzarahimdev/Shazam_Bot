from typing import Optional

import httpx


class LyricsService:
    """Lyrics via lyrics.ovh public API (free, no key). Respect provider ToS."""

    API_URL = "https://api.lyrics.ovh/v1/{artist}/{title}"

    async def get_lyrics(self, artist: str, title: str) -> Optional[str]:
        artist = artist.strip()
        title = title.strip()
        if not artist or not title:
            return None

        url = self.API_URL.format(artist=artist, title=title)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(url)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None

        lyrics = (data.get("lyrics") or "").strip()
        if not lyrics:
            return None

        # Telegram message limit safety
        if len(lyrics) > 3500:
            lyrics = lyrics[:3500] + "\n\n… (qisqartirilgan)"
        return lyrics

    @staticmethod
    def format_lyrics(artist: str, title: str, lyrics: str) -> str:
        return (
            f"🎵 <b>Song:</b> {title}\n"
            f"👤 <b>Artist:</b> {artist}\n\n"
            f"📝 <b>Lyrics:</b>\n{lyrics}"
        )
