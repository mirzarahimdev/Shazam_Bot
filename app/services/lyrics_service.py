import html
import logging
import re
from typing import Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

_lyrics_cache: dict[tuple[str, str], Optional[str]] = {}


class LyricsService:
    """Tez lyrics — faqat lyrics.ovh (2.5s), kesh bilan."""

    LYRICS_OVH = "https://api.lyrics.ovh/v1/{artist}/{title}"

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = re.sub(r"\(.*?\)", "", title)
        cleaned = re.sub(r"\[.*?\]", "", cleaned)
        cleaned = re.sub(r"\s+-\s+(feat\.|ft\.|with).*$", "", cleaned, flags=re.I)
        return " ".join(cleaned.split()).strip() or title.strip()

    async def get_lyrics(self, artist: str, title: str) -> Optional[str]:
        artist = artist.strip()
        title = title.strip()
        if not artist or not title:
            return None

        clean = self._clean_title(title)
        cache_key = (artist.lower(), clean.lower())
        if cache_key in _lyrics_cache:
            return _lyrics_cache[cache_key]

        lyrics = await self._lyrics_ovh(artist, clean)
        if not lyrics and title != clean:
            lyrics = await self._lyrics_ovh(artist, title)

        _lyrics_cache[cache_key] = lyrics
        return lyrics

    async def _lyrics_ovh(self, artist: str, title: str) -> Optional[str]:
        url = self.LYRICS_OVH.format(artist=quote(artist, safe=""), title=quote(title, safe=""))
        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return None
                data = response.json()
        except Exception:
            return None
        lyrics = (data.get("lyrics") or "").strip()
        return lyrics or None

    @staticmethod
    def format_lyrics(artist: str, title: str, lyrics: str) -> str:
        safe_artist = html.escape(artist)
        safe_title = html.escape(title)
        safe_lyrics = html.escape(lyrics)
        return (
            f"🎵 <b>{safe_artist} – {safe_title}</b>\n\n"
            f"📝 <b>Lyrics</b>\n\n"
            f"<pre>{safe_lyrics}</pre>"
        )

    @staticmethod
    def split_message(text: str, limit: int = 3900) -> list[str]:
        if len(text) <= limit:
            return [text]
        chunks: list[str] = []
        while text:
            if len(text) <= limit:
                chunks.append(text)
                break
            cut = text.rfind("\n", 0, limit)
            if cut < limit // 2:
                cut = limit
            chunks.append(text[:cut])
            text = text[cut:].lstrip("\n")
        return chunks
