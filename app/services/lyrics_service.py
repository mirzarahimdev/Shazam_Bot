import html
import re
from typing import Optional

import httpx


class LyricsService:
    """Lyrics via lyrics.ovh public API (free, no key)."""

    API_URL = "https://api.lyrics.ovh/v1/{artist}/{title}"

    @staticmethod
    def _clean_title(title: str) -> str:
        # Remove remaster/feat/from annotations that break lyrics APIs
        cleaned = re.sub(r"\(.*?\)", "", title)
        cleaned = re.sub(r"\[.*?\]", "", cleaned)
        cleaned = re.sub(r"\s+-\s+(feat\.|ft\.|with).*$", "", cleaned, flags=re.I)
        return " ".join(cleaned.split()).strip() or title.strip()

    async def get_lyrics(self, artist: str, title: str) -> Optional[str]:
        artist = artist.strip()
        title = title.strip()
        if not artist or not title:
            return None

        candidates = [title, self._clean_title(title)]
        # also try without "feat. ..."
        no_feat = re.sub(r"\s+\(feat\..*?\)", "", title, flags=re.I).strip()
        if no_feat and no_feat not in candidates:
            candidates.append(no_feat)

        for candidate in candidates:
            lyrics = await self._fetch(artist, candidate)
            if lyrics:
                return lyrics
        return None

    async def _fetch(self, artist: str, title: str) -> Optional[str]:
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
