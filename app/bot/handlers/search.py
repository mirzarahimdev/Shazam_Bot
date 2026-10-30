import logging
import shutil

import httpx
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.i18n import t
from app.bot.keyboards import (
    PAGE_SIZE,
    search_results_keyboard,
    track_actions_keyboard,
)
from app.bot.states import SearchStates
from app.config import get_settings
from app.database.models import Song
from app.database.repositories import SearchHistoryRepository, SongRepository, UserRepository
from app.services.audio_service import AudioService
from app.services.clip_service import ClipService
from app.services.lyrics_service import LyricsService
from app.services.music_service import MusicService, format_duration

router = Router(name="search")


async def _user_lang(session: AsyncSession, telegram_id: int) -> str:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    return user.language if user and user.language else "uz"


async def _download_bytes(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    except Exception:
        return None


async def _send_song_audio(
    message: Message,
    bot: Bot,
    song: Song,
    lang: str,
) -> None:
    me = await bot.get_me()
    caption = f"👉 @{me.username}" if me.username else ""
    kb = track_actions_keyboard(song_db_id=song.id, lang=lang)
    status = await message.answer("🎧 Yuklanmoqda...")

    async def _try_send(audio_input, *, title: str, performer: str, duration: int | None) -> bool:
        # Thumbnail ba'zan Telegramda xato beradi — avval usiz yuboramiz
        try:
            await message.answer_audio(
                audio=audio_input,
                title=title,
                performer=performer,
                duration=duration,
                caption=caption,
                reply_markup=kb,
            )
            return True
        except Exception as exc:
            logging.getLogger(__name__).warning("answer_audio failed: %s", exc)
            return False

    # 1) Tez va ishonchli: Deezer/iTunes preview
    if song.preview_url:
        audio_bytes = await _download_bytes(song.preview_url)
        if audio_bytes:
            safe_name = "".join(c for c in song.title if c.isalnum() or c in " -_")[:40] or "track"
            ok = await _try_send(
                BufferedInputFile(audio_bytes, filename=f"{safe_name}.mp3"),
                title=song.title,
                performer=song.artist,
                duration=30 if (song.duration or 0) > 30 else song.duration,
            )
            if ok:
                await status.delete()
                return

    # 2) To'liq trek: yt-dlp
    audio_result = await AudioService().download(song.artist, song.title)
    if audio_result and audio_result.path.exists():
        try:
            ok = await _try_send(
                FSInputFile(audio_result.path),
                title=song.title,
                performer=song.artist,
                duration=audio_result.duration or song.duration,
            )
            if ok:
                await status.delete()
                return
        finally:
            shutil.rmtree(audio_result.path.parent, ignore_errors=True)

    await status.edit_text(
        f"❌ Audio yuklab bo‘lmadi.\n🎵 <b>{song.artist} – {song.title}</b>\n{caption}",
        reply_markup=kb,
    )


def _format_results_page(query: str, lines: list[str], page: int) -> str:
    start = page * PAGE_SIZE
    chunk = lines[start : start + PAGE_SIZE]
    body = "\n".join(f"{i}. {line}" for i, line in enumerate(chunk, start=1))
    return f"<b>{query}</b>\n\n{body}"


@router.message(SearchStates.waiting_query, F.text)
async def search_query(message: Message, state: FSMContext, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    if not query or query.startswith("/"):
        return

    lang = (await state.get_data()).get("lang") or await _user_lang(session, message.from_user.id)
    if len(query) < 2:
        await message.answer(t(lang, "min_chars"))
        return

    status = await message.answer(t(lang, "searching"))

    settings = get_settings()
    music = MusicService(youtube_api_key=settings.youtube_api_key)
    tracks = await music.search(query, limit=30)

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language=lang,
    )
    await SearchHistoryRepository(session).add(user.id, query, len(tracks))

    if not tracks:
        await status.edit_text(t(lang, "not_found"))
        return

    song_repo = SongRepository(session)
    song_ids: list[int] = []
    lines: list[str] = []
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
        song_ids.append(song.id)
        lines.append(f"{track.artist} - {track.title} {format_duration(track.duration)}")

    await state.update_data(
        query=query,
        page=0,
        song_ids=song_ids,
        lines=lines,
        lang=lang,
    )

    text = _format_results_page(query, lines, 0)
    kb = search_results_keyboard(page=0, song_ids=song_ids)
    await status.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("page:"))
async def results_page(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lines: list[str] = data.get("lines") or []
    song_ids: list[int] = data.get("song_ids") or []
    query = data.get("query") or ""
    if not lines or not song_ids:
        await callback.answer("❌ Qayta qidiring", show_alert=True)
        return

    page = int(callback.data.split(":")[1])
    total_pages = max(1, (len(song_ids) + PAGE_SIZE - 1) // PAGE_SIZE)
    if page < 0 or page >= total_pages:
        await callback.answer()
        return

    await state.update_data(page=page)
    text = _format_results_page(query, lines, page)
    kb = search_results_keyboard(page=page, song_ids=song_ids)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("pick:"))
async def pick_result(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """callback_data = pick:<song_id> — raqam bosilganda shu qo'shiq chiqadi."""
    lang = await _user_lang(session, callback.from_user.id)
    try:
        song_id = int((callback.data or "").split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(t(lang, "not_found"), show_alert=True)
        return

    song = await SongRepository(session).get_by_id(song_id)
    if not song:
        await callback.answer(t(lang, "not_found"), show_alert=True)
        return

    await callback.answer()
    try:
        await _send_song_audio(callback.message, bot, song, lang)
    except Exception:
        await callback.message.answer(t(lang, "not_found"))


@router.callback_query(F.data.startswith("clip:"))
async def clip_callback(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    song_id = int(callback.data.split(":")[1])
    song = await SongRepository(session).get_by_id(song_id)
    lang = await _user_lang(session, callback.from_user.id)
    if not song:
        await callback.answer(t(lang, "not_found"), show_alert=True)
        return

    await callback.answer()
    status = await callback.message.answer("🎬 Klip yuklanmoqda...")

    clip = await ClipService().download(song.artist, song.title)
    if not clip or not clip.path.exists():
        await status.edit_text(t(lang, "not_found"))
        return

    me = await bot.get_me()
    caption = f"👉 @{me.username}" if me.username else ""
    video_file = FSInputFile(clip.path)

    try:
        await callback.message.answer_video(
            video=video_file,
            caption=caption,
            duration=clip.duration,
            width=clip.width,
            height=clip.height,
            supports_streaming=True,
        )
        await status.delete()
    except Exception:
        await status.edit_text(t(lang, "not_found"))
    finally:
        shutil.rmtree(clip.path.parent, ignore_errors=True)


@router.callback_query(F.data.startswith("lyrics:"))
async def lyrics_callback(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    song_id = int(callback.data.split(":")[1])
    song = await SongRepository(session).get_by_id(song_id)
    lang = await _user_lang(session, callback.from_user.id)
    if not song:
        await callback.answer(t(lang, "not_found"), show_alert=True)
        return

    await callback.answer()
    lyrics_service = LyricsService()
    lyrics = await lyrics_service.get_lyrics(song.artist, song.title)
    if not lyrics:
        await callback.message.answer(t(lang, "lyrics_not_found"))
        return

    me = await bot.get_me()
    footer = f"\n\n👉 @{me.username}" if me.username else ""
    text = lyrics_service.format_lyrics(song.artist, song.title, lyrics) + footer
    for chunk in lyrics_service.split_message(text):
        await callback.message.answer(chunk)
