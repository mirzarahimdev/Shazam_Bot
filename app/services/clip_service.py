import asyncio
import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.services.download_lock import run_exclusive
from app.services.media_cache import cache_key, cached_path, ensure_root, store_file

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT = 28


@dataclass
class ClipResult:
    path: Path
    title: str
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    cache_key: str = ""
    from_cache: bool = False


class ClipService:
    """Music video — bitta tez qidiruv, kesh."""

    async def download(self, artist: str, title: str, *, max_height: int = 360) -> Optional[ClipResult]:
        ensure_root()
        key = cache_key("clip", artist, title)
        hit = cached_path(key)
        if hit:
            return ClipResult(path=hit, title=title, cache_key=key, from_cache=True)

        async def _job() -> Optional[ClipResult]:
            again = cached_path(key)
            if again:
                return ClipResult(path=again, title=title, cache_key=key, from_cache=True)
            # Bitta query — kamroq kutish
            query = f"ytsearch1:{artist} {title} official music video"
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(self._download_sync, query),
                    timeout=DOWNLOAD_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning("Clip timeout: %s", query)
                result = None
            if not result:
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self._download_sync, f"ytsearch1:{artist} {title}"),
                        timeout=DOWNLOAD_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    return None
            if result:
                stored = store_file(key, result.path)
                if result.path.parent.name.startswith("clip_"):
                    shutil.rmtree(result.path.parent, ignore_errors=True)
                result.path = stored
                result.cache_key = key
            return result

        return await run_exclusive(key, _job)

    def _download_sync(self, query: str) -> Optional[ClipResult]:
        try:
            import yt_dlp
        except ImportError:
            return None

        tmp_dir = Path(tempfile.mkdtemp(prefix="clip_"))
        outtmpl = str(tmp_dir / "clip.%(ext)s")
        ydl_opts = {
            "format": "18/best[height<=360]/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "retries": 1,
            "fragment_retries": 1,
            "socket_timeout": 10,
            "geo_bypass": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if not info:
                    return None

                top = info
                if "entries" in info:
                    entries = [e for e in (info.get("entries") or []) if e]
                    if not entries:
                        return None
                    top = entries[0]

                existing = sorted(tmp_dir.glob("clip.*"), key=lambda p: p.stat().st_mtime)
                if existing and existing[-1].stat().st_size > 1000:
                    path = existing[-1]
                else:
                    requested = (top or {}).get("requested_downloads") or []
                    if requested and requested[0].get("filepath"):
                        path = Path(requested[0]["filepath"])
                    else:
                        path = Path(ydl.prepare_filename(top or info))
                        if not path.exists():
                            return None

                if path.stat().st_size > 49 * 1024 * 1024:
                    path.unlink(missing_ok=True)
                    return None

                if path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
                    renamed = path.with_suffix(".mp4")
                    try:
                        path.rename(renamed)
                        path = renamed
                    except Exception:
                        pass

                return ClipResult(
                    path=path,
                    title=(top or {}).get("title") or query,
                    duration=(top or {}).get("duration"),
                    width=(top or {}).get("width"),
                    height=(top or {}).get("height"),
                )
        except Exception as exc:
            logger.warning("Clip download failed (%s): %s", query, exc)
            return None
