from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_menu_keyboard
from app.database.repositories import (
    FavoriteRepository,
    RecognizedSongRepository,
    SavedVideoRepository,
    SearchHistoryRepository,
    UserRepository,
)

router = Router(name="profile")


@router.message(F.text == "👤 Profil")
async def profile(message: Message, session: AsyncSession) -> None:
    tg = message.from_user
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=tg.id,
        username=tg.username,
        first_name=tg.first_name,
        last_name=tg.last_name,
    )

    searches = await SearchHistoryRepository(session).count_by_user(user.id)
    recognized = await RecognizedSongRepository(session).count_by_user(user.id)
    videos = await SavedVideoRepository(session).count_by_user(user.id)
    favorites = await FavoriteRepository(session).count_by_user(user.id)

    name = " ".join(x for x in [user.first_name, user.last_name] if x) or "—"
    created = user.created_at.strftime("%Y-%m-%d") if user.created_at else "—"

    text = (
        "👤 <b>Profil</b>\n\n"
        f"👤 Ism: {name}\n"
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"🔗 Username: @{user.username or '—'}\n"
        f"🎵 Qidirilgan qo‘shiqlar: {searches}\n"
        f"🎧 Aniqlangan qo‘shiqlar: {recognized}\n"
        f"💾 Saqlangan videolar: {videos}\n"
        f"⭐️ Sevimlilar: {favorites}\n"
        f"📅 Ro‘yxatdan o‘tgan: {created}"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())
