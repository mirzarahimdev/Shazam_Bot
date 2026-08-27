from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import settings_keyboard
from app.database.repositories import SettingsRepository, UserRepository

router = Router(name="settings")


@router.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )
    settings = await SettingsRepository(session).get_by_user(user.id)
    lang = settings.language if settings else user.language
    notif = settings.notifications_enabled if settings else True
    await message.answer(
        "⚙️ <b>Sozlamalar</b>\nTil va bildirishnomalarni tanlang:",
        reply_markup=settings_keyboard(lang, notif),
    )


@router.callback_query(F.data.startswith("settings:lang:"))
async def set_language(callback: CallbackQuery, session: AsyncSession) -> None:
    lang = callback.data.split(":")[-1]
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    user.language = lang
    settings = await SettingsRepository(session).update_language(user.id, lang)
    await callback.message.edit_reply_markup(
        reply_markup=settings_keyboard(settings.language, settings.notifications_enabled)
    )
    await callback.answer(f"Til: {lang.upper()}")


@router.callback_query(F.data == "settings:notif")
async def toggle_notif(callback: CallbackQuery, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    settings = await SettingsRepository(session).toggle_notifications(user.id)
    await callback.message.edit_reply_markup(
        reply_markup=settings_keyboard(settings.language, settings.notifications_enabled)
    )
    await callback.answer("Bildirishnomalar yangilandi")


@router.callback_query(F.data == "settings:noop")
async def settings_noop(callback: CallbackQuery) -> None:
    await callback.answer()
