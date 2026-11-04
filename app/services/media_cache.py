"""Disk + Telegram file_id cache — bir xil qo‘shiqni qayta yuklamaslik."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Optional

CACHE_ROOT = Path("data/media_cache")
_file_ids: dict[str, str] = {}
_inflight: dict[str, object] = {}


def _slug(text: str) -> str:
    text = re.sub(r"[^\w\s-]+", "", text, flags=re.U).strip().lower()
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:60] or "track"


def cache_key(kind: str, artist: str, title: str) -> str:
    raw = f"{kind}|{artist.strip().lower()}|{title.strip().lower()}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"{kind}_{_slug(artist)}_{_slug(title)}_{digest}"


def get_file_id(key: str) -> Optional[str]:
    return _file_ids.get(key)


def set_file_id(key: str, file_id: str) -> None:
    if file_id:
        _file_ids[key] = file_id


def cached_path(key: str) -> Optional[Path]:
    folder = CACHE_ROOT / key
    if not folder.is_dir():
        return None
    files = [p for p in folder.iterdir() if p.is_file() and p.stat().st_size > 1000]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def store_file(key: str, src: Path) -> Path:
    folder = CACHE_ROOT / key
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / src.name
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return dest


def ensure_root() -> None:
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
