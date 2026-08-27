from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_menu_keyboard
from app.database.repositories import FavoriteRepository, UserRepository

router = Router(name="favorites")


@router.message(F.text == "⭐️ Sevimlilar")
async def favorites_list(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    items = await FavoriteRepository(session).list_by_user(user.id)
    if not items:
        await message.answer("⭐️ Sevimlilar bo‘sh.", reply_markup=main_menu_keyboard())
        return

    lines = ["⭐️ <b>Sevimlilar</b>\n"]
    for item in items:
        lines.append(f"• [{item.item_type}] {item.title or item.item_id}")
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())
