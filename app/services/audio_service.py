import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    path: Path
    title: str
    artist: str
    duration: Optional[int] = None


class AudioService:
    """Download audio track for native Telegram playback (via yt-dlp)."""

    async def download(self, artist: str, title: str) -> Optional[AudioResult]:
        query = f"{artist} {title} audio".strip()
        return await asyncio.to_thread(self._download_sync, query, artist, title)

    def _download_sync(self, query: str, artist: str, title: str) -> Optional[AudioResult]:
        try:
            import yt_dlp
        except ImportError:
            return None

        tmp_dir = Path(tempfile.mkdtemp(prefix="audio_"))
        outtmpl = str(tmp_dir / "audio.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch1",
            "retries": 3,
            "socket_timeout": 45,
            "geo_bypass": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if not info:
                    return None
                if "entries" in info:
                    entries = [e for e in (info.get("entries") or []) if e]
                    if not entries:
                        return None
                    info = entries[0]

                requested = info.get("requested_downloads") or []
                if requested and requested[0].get("filepath"):
                    path = Path(requested[0]["filepath"])
                else:
                    path = Path(ydl.prepare_filename(info))
                    if not path.exists():
                        matches = sorted(tmp_dir.glob("audio.*"), key=lambda p: p.stat().st_mtime)
                        if not matches:
                            return None
                        path = matches[-1]

                if not path.exists() or path.stat().st_size < 1000:
                    return None

                return AudioResult(
                    path=path,
                    title=title or info.get("title") or query,
                    artist=artist or info.get("uploader") or "",
                    duration=info.get("duration"),
                )
        except Exception as exc:
            logger.warning("Audio download failed for %s - %s: %s", artist, title, exc)
            return None
