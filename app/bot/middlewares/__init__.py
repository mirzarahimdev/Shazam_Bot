from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from redis.asyncio import Redis

from app.config import get_settings
from app.database import async_session_factory
from app.database.repositories import UserRepository


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user:
            session = data.get("session")
            if session is not None:
                repo = UserRepository(session)
                if await repo.is_blocked(user.id):
                    if isinstance(event, Message):
                        await event.answer("🚫 Siz bloklangansiz.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("🚫 Siz bloklangansiz.", show_alert=True)
                    return None
        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis):
        self.redis = redis
        self.limit = get_settings().rate_limit_per_minute

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user:
            key = f"rl:{user.id}"
            try:
                count = await self.redis.incr(key)
                if count == 1:
                    await self.redis.expire(key, 60)
                if count > self.limit:
                    if isinstance(event, Message):
                        await event.answer("⏳ Juda ko‘p so‘rov. Biroz kuting.")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⏳ Juda ko‘p so‘rov.", show_alert=True)
                    return None
            except Exception:
                # Redis down — do not block the bot
                pass

        return await handler(event, data)
