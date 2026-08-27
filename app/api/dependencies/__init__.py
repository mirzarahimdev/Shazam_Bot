from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def verify_admin(
    x_admin_id: int | None = Header(default=None, alias="X-Admin-Id"),
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
) -> int:
    settings = get_settings()
    if (
        x_admin_id is None
        or x_admin_id not in settings.admin_ids
        or not x_admin_secret
        or x_admin_secret != settings.webhook_secret
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return x_admin_id


async def verify_webhook_secret(
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    if settings.webhook_secret and x_telegram_bot_api_secret_token != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")
