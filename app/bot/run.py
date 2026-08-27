import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import get_routers
from app.bot.middlewares import BanCheckMiddleware, DbSessionMiddleware, RateLimitMiddleware
from app.config import get_settings
from app.database import init_db

logging.basicConfig(level=logging.INFO)
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

        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        dp.update.middleware(RateLimitMiddleware(redis))
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — rate limit o‘chirilgan", exc)
        redis = None

    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(BanCheckMiddleware())

    for router in get_routers():
        dp.include_router(router)

    me = await bot.get_me()
    logger.info("MusicSave bot started as @%s (polling)", me.username)
    try:
        await dp.start_polling(bot)
    finally:
        if redis is not None:
            await redis.aclose()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
