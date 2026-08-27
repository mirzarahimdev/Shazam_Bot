import tempfile
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import main_menu_keyboard, recognition_actions_keyboard
from app.bot.states import RecognizeStates
from app.config import get_settings
from app.database.repositories import RecognizedSongRepository, SongRepository, UserRepository
from app.services.music_service import MusicService
from app.services.recognition_service import RecognitionService

router = Router(name="recognize")


@router.message(F.text == "🎧 Qo‘shiqni aniqlash")
async def recognize_entry(message: Message, state: FSMContext) -> None:
    await state.set_state(RecognizeStates.waiting_media)
    await message.answer(
        "🎧 Audio, voice yoki qisqa video yuboring.\n"
        "Bot AudD orqali qo‘shiqni aniqlaydi.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(RecognizeStates.waiting_media, F.voice | F.audio | F.video | F.video_note)
async def recognize_media(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    settings = get_settings()
    recognition = RecognitionService(settings.audd_api_token)
    if not recognition.is_configured:
        await message.answer(
            "⚠️ Music recognition sozlanmagan.\n"
            "<code>AUDD_API_TOKEN</code> ni .env ga qo‘ying.\n"
            "Token: https://dashboard.audd.io/"
        )
        return

    file_id = None
    filename = "media.bin"
    file_size = None

    if message.voice:
        file_id = message.voice.file_id
        filename = "voice.ogg"
        file_size = message.voice.file_size
    elif message.audio:
        file_id = message.audio.file_id
        filename = message.audio.file_name or "audio.mp3"
        file_size = message.audio.file_size
    elif message.video:
        file_id = message.video.file_id
        filename = "video.mp4"
        file_size = message.video.file_size
    elif message.video_note:
        file_id = message.video_note.file_id
        filename = "video_note.mp4"
        file_size = message.video_note.file_size

    if not file_id:
        await message.answer("❌ Media topilmadi.")
        return

    if file_size and file_size > settings.max_media_size_bytes:
        await message.answer(f"❌ Fayl juda katta. Max: {settings.max_media_size_mb} MB")
        return

    status = await message.answer("🎧 Aniqlanmoqda...")

    try:
        tg_file = await bot.get_file(file_id)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / filename
            await bot.download_file(tg_file.file_path, destination=path)
            file_bytes = path.read_bytes()

        result = await recognition.recognize_bytes(file_bytes, filename=filename)
    except Exception as exc:
        await status.edit_text(f"❌ Xatolik: {exc}")
        return

    if not result:
        await status.edit_text("❌ Qo‘shiqni aniqlab bo‘lmadi. Boshqa audio yuborib ko‘ring.")
        return

    music = MusicService(youtube_api_key=settings.youtube_api_key)
    video = await music.find_official_video(result.artist, result.title)
    result.video_url = video["url"]

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    song = await SongRepository(session).upsert(
        external_id=None,
        title=result.title,
        artist=result.artist,
        album=result.album,
        cover_url=result.cover_url,
        preview_url=result.preview_url,
        source_url=result.source_url,
        video_url=result.video_url,
        provider="audd",
    )

    await RecognizedSongRepository(session).add(
        user_id=user.id,
        title=result.title,
        artist=result.artist,
        album=result.album,
        cover_url=result.cover_url,
        source_url=result.source_url,
        video_url=result.video_url,
        song_id=song.id,
    )

    text = (
        f"🎵 <b>{result.title}</b>\n"
        f"👤 {result.artist}\n"
        f"💿 {result.album or '—'}\n"
    )
    kb = recognition_actions_keyboard(
        title=result.title,
        artist=result.artist,
        source_url=result.source_url,
        video_url=result.video_url,
    )

    await status.delete()
    if result.cover_url:
        await message.answer_photo(result.cover_url, caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
