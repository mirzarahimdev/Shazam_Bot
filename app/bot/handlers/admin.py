from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import admin_keyboard
from app.config import get_settings
from app.database.repositories import (
    RecognizedSongRepository,
    SavedVideoRepository,
    SearchHistoryRepository,
    StatsRepository,
    UserRepository,
)

router = Router(name="admin")


def _is_admin(user_id: int) -> bool:
    return user_id in get_settings().admin_ids


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    users = await UserRepository(session).count_all()
    videos = await SavedVideoRepository(session).count_all()
    period = await StatsRepository(session).daily_weekly()

    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"💾 Saqlangan videolar: {videos}\n\n"
        f"📅 24 soat:\n"
        f"• Yangi userlar: {period['users_last_24h']}\n"
        f"• Qidiruvlar: {period['searches_last_24h']}\n"
        f"• Aniqlashlar: {period['recognized_last_24h']}\n"
        f"• Videolar: {period['videos_last_24h']}\n\n"
        f"📆 7 kun:\n"
        f"• Yangi userlar: {period['users_last_7d']}\n"
        f"• Qidiruvlar: {period['searches_last_7d']}"
    )
    await callback.message.answer(text, reply_markup=admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:top_search")
async def admin_top_search(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    rows = await SearchHistoryRepository(session).top_queries(10)
    if not rows:
        await callback.message.answer("Ma’lumot yo‘q.")
    else:
        lines = ["🎵 <b>Eng ko‘p qidirilganlar</b>\n"]
        for i, (query, cnt) in enumerate(rows, 1):
            lines.append(f"{i}. {query} — {cnt}")
        await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "admin:top_recog")
async def admin_top_recog(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return
    rows = await RecognizedSongRepository(session).top_songs(10)
    if not rows:
        await callback.message.answer("Ma’lumot yo‘q.")
    else:
        lines = ["🎧 <b>Eng ko‘p aniqlanganlar</b>\n"]
        for i, (title, artist, cnt) in enumerate(rows, 1):
            lines.append(f"{i}. {artist} — {title} ({cnt})")
        await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.message(Command("block"))
async def block_user(message: Message, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        await message.answer("⛔ Ruxsat yo‘q.")
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /block TELEGRAM_ID")
        return
    tg_id = int(parts[1])
    ok = await UserRepository(session).set_blocked(tg_id, True)
    await message.answer("🚫 Bloklandi." if ok else "User topilmadi.")


@router.message(Command("unblock"))
async def unblock_user(message: Message, session: AsyncSession) -> None:
    if not message.from_user or not _is_admin(message.from_user.id):
        await message.answer("⛔ Ruxsat yo‘q.")
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Foydalanish: /unblock TELEGRAM_ID")
        return
    tg_id = int(parts[1])
    ok = await UserRepository(session).set_blocked(tg_id, False)
    await message.answer("✅ Blokdan chiqarildi." if ok else "User topilmadi.")
