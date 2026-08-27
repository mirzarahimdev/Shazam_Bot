from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import admin_keyboard, main_menu_keyboard
from app.config import get_settings
from app.database.repositories import UserRepository

router = Router(name="start")

START_TEXT = (
    "🎵 Salom! <b>MusicSave</b> botiga xush kelibsiz.\n\n"
    "Bu bot orqali:\n"
    "🎵 Musiqa qidirish\n"
    "🎧 Qo‘shiqni aniqlash\n"
    "📝 Lyrics ko‘rish\n"
    "🎬 Rasmiy klipni topish\n"
    "💾 Videolarni saqlash\n"
    "mumkin."
)


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

    await message.answer(START_TEXT, reply_markup=main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Yordam:\n"
        "• 🎵 Musiqa qidirish — qo‘shiq/ijrochi nomini yuboring\n"
        "• 🎧 Qo‘shiqni aniqlash — audio/voice/video yuboring\n"
        "• 💾 Video Save — o‘z videolaringizni saqlang\n"
        "• /admin — faqat adminlar uchun"
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    settings = get_settings()
    if not message.from_user or message.from_user.id not in settings.admin_ids:
        await message.answer("⛔ Ruxsat yo‘q.")
        return
    await message.answer("🛠 Admin panel", reply_markup=admin_keyboard())


@router.message(F.text == "🏠 Menyuga qaytish")
async def back_to_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())
