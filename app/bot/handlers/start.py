from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.i18n import LANGUAGE_PROMPT, SUPPORTED_LANGS, t
from app.bot.keyboards import admin_keyboard, language_keyboard
from app.bot.states import SearchStates
from app.config import get_settings
from app.database.repositories import UserRepository

router = Router(name="start")


async def _user_lang(session: AsyncSession, telegram_id: int) -> str:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    return user.language if user and user.language else "uz"


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = message.from_user
    if not user:
        return

    repo = UserRepository(session)
    await repo.get_or_create(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language=user.language_code or "uz",
    )

    await message.answer(LANGUAGE_PROMPT, reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def language_chosen(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    lang = (callback.data or "").split(":", 1)[-1]
    if lang not in SUPPORTED_LANGS:
        await callback.answer("Language not supported", show_alert=True)
        return

    user = callback.from_user
    if not user:
        await callback.answer()
        return

    repo = UserRepository(session)
    db_user = await repo.get_by_telegram_id(user.id)
    if not db_user:
        await repo.get_or_create(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language=lang,
        )
    await repo.set_language(user.id, lang)

    await state.set_state(SearchStates.waiting_query)
    await state.update_data(lang=lang)

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        t(lang, "lang_saved"),
        reply_markup=ReplyKeyboardRemove(),
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession) -> None:
    if not message.from_user:
        return
    lang = await _user_lang(session, message.from_user.id)
    await message.answer(t(lang, "help"))


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    settings = get_settings()
    if not message.from_user or message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ Ruxsat yo‘q.")
        return
    await message.answer("🛠 Admin panel", reply_markup=admin_keyboard())
