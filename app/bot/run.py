import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from app.bot.handlers import get_routers
from app.bot.middlewares import BanCheckMiddleware, DbSessionMiddleware, RateLimitMiddleware
from app.config import get_settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# httpx/yt-dlp shovqinini kamaytirish
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    redis = None
    try:
        from redis.asyncio import Redis

        redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.4,
            socket_timeout=0.4,
        )
        await redis.ping()
        dp.update.middleware(RateLimitMiddleware(redis))
        logger.info("Redis connected")
    except Exception:
        logger.info("Redis yo‘q — rate limit o‘chirilgan")
        if redis is not None:
            try:
                await redis.aclose()
            except Exception:
                pass
        redis = None

    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(BanCheckMiddleware())

    for router in get_routers():
        dp.include_router(router)

    @dp.errors()
    async def _on_error(event: ErrorEvent) -> bool:
        logger.exception("Unhandled update error: %s", event.exception)
        return True

    me = await bot.get_me()
    logger.info("Bot started as @%s (polling)", me.username)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if redis is not None:
            await redis.aclose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
