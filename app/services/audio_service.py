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

DOWNLOAD_TIMEOUT = 25


@dataclass
class AudioResult:
    path: Path
    title: str
    artist: str
    duration: Optional[int] = None
    cache_key: str = ""
    from_cache: bool = False


class AudioService:
    """YouTube audio (m4a/140) + disk cache. ffmpeg shart emas."""

    async def download(self, artist: str, title: str) -> Optional[AudioResult]:
        ensure_root()
        key = cache_key("audio", artist, title)
        hit = cached_path(key)
        if hit:
            return AudioResult(
                path=hit, title=title, artist=artist, cache_key=key, from_cache=True
            )

        async def _job() -> Optional[AudioResult]:
            again = cached_path(key)
            if again:
                return AudioResult(
                    path=again, title=title, artist=artist, cache_key=key, from_cache=True
                )
            for query in (
                f"ytsearch1:{artist} {title} official audio",
                f"ytsearch1:{artist} {title}",
            ):
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self._download_sync, query, artist, title),
                        timeout=DOWNLOAD_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    logger.warning("Audio timeout: %s", query)
                    continue
                if result:
                    stored = store_file(key, result.path)
                    if result.path.parent.name.startswith("audio_"):
                        shutil.rmtree(result.path.parent, ignore_errors=True)
                    result.path = stored
                    result.cache_key = key
                    return result
            return None

        return await run_exclusive(key, _job)

    def _download_sync(self, query: str, artist: str, title: str) -> Optional[AudioResult]:
        try:
            import yt_dlp
        except ImportError:
            return None

        tmp_dir = Path(tempfile.mkdtemp(prefix="audio_"))
        outtmpl = str(tmp_dir / "audio.%(ext)s")
        ydl_opts = {
            # 140 = m4a — Telegram answer_audio uchun eng barqaror (ffmpeg yo‘q)
            "format": "140/bestaudio[ext=m4a]/bestaudio[acodec=mp4a.40.2]/bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "retries": 1,
            "fragment_retries": 1,
            "socket_timeout": 12,
            "geo_bypass": True,
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
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

                path = self._resolve_path(ydl, info, tmp_dir)
                if not path or not path.exists() or path.stat().st_size < 1000:
                    return None

                # Telegram: fayl nomi kengaytmasi muhim
                if path.suffix.lower() not in {".m4a", ".mp3", ".aac", ".ogg"}:
                    renamed = path.with_suffix(".m4a")
                    try:
                        path.rename(renamed)
                        path = renamed
                    except Exception:
                        pass

                return AudioResult(
                    path=path,
                    title=title or info.get("title") or query,
                    artist=artist or info.get("uploader") or "",
                    duration=info.get("duration"),
                )
        except Exception as exc:
            logger.warning("Audio download failed (%s): %s", query, exc)
            return None

    @staticmethod
    def _resolve_path(ydl, info: dict, tmp_dir: Path) -> Optional[Path]:
        requested = info.get("requested_downloads") or []
        if requested and requested[0].get("filepath"):
            return Path(requested[0]["filepath"])
        path = Path(ydl.prepare_filename(info))
        if path.exists():
            return path
        matches = sorted(tmp_dir.glob("audio.*"), key=lambda p: p.stat().st_mtime)
        return matches[-1] if matches else None
