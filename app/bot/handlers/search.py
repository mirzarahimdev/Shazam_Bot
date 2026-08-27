from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.constants import MENU_BUTTONS
from app.bot.keyboards import clip_keyboard, main_menu_keyboard, track_actions_keyboard
from app.bot.states import SearchStates
from app.config import get_settings
from app.database.repositories import FavoriteRepository, SearchHistoryRepository, SongRepository, UserRepository
from app.services.lyrics_service import LyricsService
from app.services.music_service import MusicService

router = Router(name="search")


@router.message(F.text == "🎵 Musiqa qidirish")
async def search_entry(message: Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_query)
    await message.answer(
        "🔍 Qo‘shiq yoki ijrochi nomini yuboring.\n"
        "Masalan: <code>Imagine Dragons Believer</code>",
        reply_markup=main_menu_keyboard(),
    )


@router.message(SearchStates.waiting_query, F.text, ~F.text.in_(MENU_BUTTONS))
async def search_query(message: Message, state: FSMContext, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    if not query or query.startswith("/"):
        return

    if len(query) < 2:
        await message.answer("Kamida 2 ta belgi yuboring.")
        return

    await message.answer("🔎 Qidirilmoqda...")

    settings = get_settings()
    music = MusicService(youtube_api_key=settings.youtube_api_key)
    tracks = await music.search(query, limit=5)

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    history = SearchHistoryRepository(session)
    await history.add(user.id, query, len(tracks))

    if not tracks:
        await message.answer("❌ Natija topilmadi. Boshqa so‘rov yuboring.")
        return

    song_repo = SongRepository(session)
    for track in tracks:
        song = await song_repo.upsert(
            external_id=track.external_id,
            title=track.title,
            artist=track.artist,
            album=track.album,
            cover_url=track.cover_url,
            duration=track.duration,
            preview_url=track.preview_url,
            source_url=track.source_url,
            video_url=track.video_url,
            provider=track.provider,
        )
        text = music.format_track_message(track)
        kb = track_actions_keyboard(
            song_db_id=song.id,
            preview_url=track.preview_url,
            video_url=track.video_url,
            artist=track.artist,
            title=track.title,
        )
        if track.cover_url:
            await message.answer_photo(track.cover_url, caption=text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)

    await state.set_state(SearchStates.waiting_query)


@router.callback_query(F.data.startswith("listen:"))
async def listen_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    song_id = int(callback.data.split(":")[1])
    song = await SongRepository(session).get_by_id(song_id)
    if not song:
        await callback.answer("Topilmadi", show_alert=True)
        return
    if song.preview_url:
        await callback.message.answer(f"🎧 Preview: {song.preview_url}")
    elif song.source_url:
        await callback.message.answer(f"🔗 Rasmiy manba: {song.source_url}")
    else:
        await callback.message.answer("❌ Tinglash havolasi mavjud emas.")
    await callback.answer()


@router.callback_query(F.data.startswith("clip:"))
async def clip_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    song_id = int(callback.data.split(":")[1])
    song = await SongRepository(session).get_by_id(song_id)
    if not song:
        await callback.answer("Topilmadi", show_alert=True)
        return

    settings = get_settings()
    music = MusicService(youtube_api_key=settings.youtube_api_key)
    video = await music.find_official_video(song.artist, song.title)

    text = (
        "🎬 <b>Official Music Video</b>\n\n"
        f"🎵 {video['title']}\n"
    )
    if video.get("duration"):
        text += f"⏱️ {video['duration']}\n"
    text += "\nCopyright himoyalangan videolar yuklab olinmaydi — faqat rasmiy havola beriladi."

    if video.get("thumbnail"):
        await callback.message.answer_photo(
            video["thumbnail"],
            caption=text,
            reply_markup=clip_keyboard(video["url"]),
        )
    else:
        await callback.message.answer(text, reply_markup=clip_keyboard(video["url"]))
    await callback.answer()


@router.callback_query(F.data.startswith("lyrics:"))
async def lyrics_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    song_id = int(callback.data.split(":")[1])
    song = await SongRepository(session).get_by_id(song_id)
    if not song:
        await callback.answer("Topilmadi", show_alert=True)
        return

    lyrics_service = LyricsService()
    lyrics = await lyrics_service.get_lyrics(song.artist, song.title)
    if not lyrics:
        await callback.message.answer("❌ Bu qo‘shiq uchun lyrics topilmadi.")
    else:
        await callback.message.answer(lyrics_service.format_lyrics(song.artist, song.title, lyrics))
    await callback.answer()


@router.callback_query(F.data.startswith("lyrics_text:"))
async def lyrics_text_callback(callback: CallbackQuery) -> None:
    payload = callback.data.split(":", 1)[1]
    if "|" not in payload:
        await callback.answer("Xato", show_alert=True)
        return
    artist, title = payload.split("|", 1)
    lyrics_service = LyricsService()
    lyrics = await lyrics_service.get_lyrics(artist, title)
    if not lyrics:
        await callback.message.answer("❌ Bu qo‘shiq uchun lyrics topilmadi.")
    else:
        await callback.message.answer(lyrics_service.format_lyrics(artist, title, lyrics))
    await callback.answer()


@router.callback_query(F.data.startswith("fav:"))
async def favorite_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    # fav:song:123 or fav:artist:Name
    parts = callback.data.split(":", 2)
    if len(parts) < 3:
        await callback.answer("Xato", show_alert=True)
        return

    item_type, item_id = parts[1], parts[2]
    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    title = item_id
    if item_type == "song":
        song = await SongRepository(session).get_by_id(int(item_id))
        if song:
            title = f"{song.artist} — {song.title}"

    fav_repo = FavoriteRepository(session)
    _, created = await fav_repo.add(
        user_id=user.id,
        item_type=item_type,
        item_id=item_id,
        title=title,
    )
    if created:
        await callback.answer("⭐️ Sevimlilarga qo‘shildi")
    else:
        await callback.answer("Allaqachon sevimlilarda")
