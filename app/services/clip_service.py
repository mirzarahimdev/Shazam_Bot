import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ClipResult:
    path: Path
    title: str
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


class ClipService:
    """Download a music video for native Telegram playback (via yt-dlp)."""

    async def download(self, artist: str, title: str, *, max_height: int = 480) -> Optional[ClipResult]:
        query = f"{artist} {title} official music video".strip()
        # Try progressive mp4 first (no ffmpeg merge needed), then any best
        for fmt in (
            f"best[height<= {max_height}][ext=mp4]/best[ext=mp4]/best".replace("<= ", "<="),
            "best",
        ):
            result = await asyncio.to_thread(self._download_sync, query, fmt)
            if result:
                return result
        return None

    def _download_sync(self, query: str, fmt: str) -> Optional[ClipResult]:
        try:
            import yt_dlp
        except ImportError:
            return None

        tmp_dir = Path(tempfile.mkdtemp(prefix="clip_"))
        outtmpl = str(tmp_dir / "clip.%(ext)s")
        ydl_opts = {
            "format": fmt,
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
                        matches = sorted(tmp_dir.glob("clip.*"), key=lambda p: p.stat().st_mtime)
                        if not matches:
                            return None
                        path = matches[-1]

                if not path.exists() or path.stat().st_size < 1000:
                    return None

                return ClipResult(
                    path=path,
                    title=info.get("title") or query,
                    duration=info.get("duration"),
                    width=info.get("width"),
                    height=info.get("height"),
                )
        except Exception as exc:
            logger.warning("Clip download failed (%s) for %s: %s", fmt, query, exc)
            return None
