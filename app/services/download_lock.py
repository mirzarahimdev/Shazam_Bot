"""Bir xil trek uchun parallel yt-dlp ni birlashtirish + concurrent limit."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

_semaphore = asyncio.Semaphore(3)  # tugma bosilganda warmup bilan urilmasin
_inflight: dict[str, asyncio.Task] = {}


async def run_exclusive(key: str, factory: Callable[[], Awaitable[T]]) -> T:
    existing = _inflight.get(key)
    if existing is not None and not existing.done():
        return await existing  # type: ignore[return-value]

    async def _wrapped() -> T:
        async with _semaphore:
            return await factory()

    task: asyncio.Task[T] = asyncio.create_task(_wrapped())
    _inflight[key] = task
    try:
        return await task
    finally:
        if _inflight.get(key) is task:
            _inflight.pop(key, None)
