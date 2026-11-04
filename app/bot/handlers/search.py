import asyncio
import html
import logging
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote_plus

import httpx
from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.i18n import t
from app.bot.keyboards import PAGE_SIZE, search_results_keyboard, track_actions_keyboard
from app.bot.states import SearchStates
from app.config import get_settings
from app.database.models import Song
from app.database.repositories import SearchHistoryRepository, SongRepository, UserRepository
from app.services.audio_service import AudioResult, AudioService
from app.services.clip_service import ClipResult, ClipService
from app.services.lyrics_service import LyricsService
from app.services.media_cache import cache_key, cached_path, get_file_id, set_file_id
from app.services.music_service import MusicService, format_duration

router = Router(name="search")
logger = logging.getLogger(__name__)

_cached_caption: str | None = None
# chat_id -> {job_kind -> Task}
_chat_jobs: dict[int, dict[str, asyncio.Task]] = {}
# Tez tugmalar: DB/HTTP kutmaslik
_song_snap_cache: dict[int, "SongSnap"] = {}
_preview_bytes_cache: dict[str, bytes] = {}


@dataclass
class SongSnap:
    """ORM sessiyasidan mustaqil snapshot — fonda yuklash uchun."""

    id: int
    title: str
    artist: str
    album: Optional[str]
    duration: Optional[int]
    preview_url: Optional[str]
    cover_url: Optional[str]
    video_url: Optional[str]

    @classmethod
    def from_song(cls, song: Song) -> "SongSnap":
        return cls(
            id=song.id,
            title=song.title or "",
            artist=song.artist or "",
            album=song.album,
            duration=song.duration,
            preview_url=song.preview_url,
            cover_url=song.cover_url,
            video_url=song.video_url,
        )


def _cancel_job(chat_id: int, kind: str) -> None:
    jobs = _chat_jobs.get(chat_id) or {}
    task = jobs.pop(kind, None)
    if task and not task.done():
        task.cancel()


def _cancel_warms(chat_id: int) -> None:
    """Tugma bosilganda fon warmup yuklashni to‘xtat — tugma birinchi bo‘lsin."""
    _cancel_job(chat_id, "warm_audio")
    _cancel_job(chat_id, "warm_clip")
    _cancel_job(chat_id, "warm_preview")


def _spawn(chat_id: int, kind: str, coro) -> None:
    """Handler tez qaytsin. Bir chatda bir xil ish — eski vazifa bekor."""
    jobs = _chat_jobs.setdefault(chat_id, {})
    if kind in {"listen", "audio", "clip", "lyrics"}:
        _cancel_warms(chat_id)
    if kind in {"clip", "lyrics"}:
        audio_task = jobs.pop("audio", None)
        if audio_task and not audio_task.done():
            audio_task.cancel()
    old = jobs.pop(kind, None)
    if old and not old.done():
        old.cancel()

    task = asyncio.create_task(coro)
    jobs[kind] = task

    def _done(t: asyncio.Task) -> None:
        current = _chat_jobs.get(chat_id, {})
        if current.get(kind) is t:
            current.pop(kind, None)
        if not current:
            _chat_jobs.pop(chat_id, None)
        try:
            t.result()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("bg job %s failed: %s", kind, exc)

    task.add_done_callback(_done)


async def _user_lang(session: AsyncSession, telegram_id: int) -> str:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    return user.language if user and user.language else "uz"


async def _download_bytes(url: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    except Exception:
        return None


async def _bot_caption(bot: Bot) -> str:
    global _cached_caption
    if _cached_caption is not None:
        return _cached_caption
    me = await bot.get_me()
    _cached_caption = f"👉 @{me.username}" if me.username else ""
    return _cached_caption


async def _send_preview(message: Message, song: SongSnap, caption: str) -> bool:
    if not song.preview_url:
        return False
    key = cache_key("preview", song.artist, song.title)
    audio_bytes = _preview_bytes_cache.get(key)
    if not audio_bytes:
        audio_bytes = await _download_bytes(song.preview_url)
        if audio_bytes:
            _preview_bytes_cache[key] = audio_bytes
    if not audio_bytes:
        return False
    safe_name = "".join(c for c in song.title if c.isalnum() or c in " -_")[:40] or "track"
    try:
        await message.answer_audio(
            audio=BufferedInputFile(audio_bytes, filename=f"{safe_name}.mp3"),
            title=song.title,
            performer=song.artist,
            duration=30 if (song.duration or 0) > 30 else song.duration,
            caption=caption,
        )
        return True
    except Exception as exc:
        logger.warning("preview audio failed: %s", exc)
        return False


async def _warm_preview_cache(song: SongSnap) -> None:
    """Preview baytlarni xotiraga — Tinglash deyarli darhol."""
    try:
        if not song.preview_url:
            return
        key = cache_key("preview", song.artist, song.title)
        if key in _preview_bytes_cache:
            return
        data = await _download_bytes(song.preview_url)
        if data:
            _preview_bytes_cache[key] = data
    except Exception as exc:
        logger.debug("warm preview failed: %s", exc)


async def _warm_audio_cache(song: SongSnap) -> None:
    """Kechiktirilgan warmup — tugmani to‘smaslik uchun."""
    try:
        await asyncio.sleep(8)
        key = cache_key("audio", song.artist, song.title)
        if get_file_id(key) or cached_path(key):
            return
        await AudioService().download(song.artist, song.title)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.debug("warm audio failed: %s", exc)


async def _warm_clip_cache(song: SongSnap) -> None:
    """Kechiktirilgan klip warmup."""
    try:
        await asyncio.sleep(10)
        key = cache_key("clip", song.artist, song.title)
        if get_file_id(key) or cached_path(key):
            return
        await ClipService().download(song.artist, song.title)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.debug("warm clip failed: %s", exc)


def _safe_filename(name: str, ext: str) -> str:
    base = "".join(c for c in name if c.isalnum() or c in " -_")[:50].strip() or "track"
    return f"{base}.{ext.lstrip('.')}"


async def _deliver_audio(
    message: Message,
    song: SongSnap,
    caption: str,
    audio_result: AudioResult | None,
) -> bool:
    key = cache_key("audio", song.artist, song.title)
    file_id = get_file_id(key)
    if file_id:
        try:
            await message.answer_audio(
                audio=file_id,
                title=song.title,
                performer=song.artist,
                duration=song.duration,
                caption=caption,
            )
            return True
        except Exception:
            pass

    if audio_result and audio_result.path.exists():
        ext = audio_result.path.suffix.lstrip(".") or "m4a"
        try:
            msg = await message.answer_audio(
                audio=FSInputFile(
                    audio_result.path,
                    filename=_safe_filename(f"{song.artist} - {song.title}", ext),
                ),
                title=song.title,
                performer=song.artist,
                duration=audio_result.duration or song.duration,
                caption=caption,
            )
            if msg.audio and msg.audio.file_id:
                set_file_id(audio_result.cache_key or key, msg.audio.file_id)
            return True
        except Exception as exc:
            logger.warning("answer_audio failed: %s", exc)
            try:
                await message.answer_document(
                    document=FSInputFile(
                        audio_result.path,
                        filename=_safe_filename(f"{song.artist} - {song.title}", ext),
                    ),
                    caption=caption,
                )
                return True
            except Exception as exc2:
                logger.warning("audio document fallback failed: %s", exc2)
    return False


async def _deliver_clip(
    message: Message,
    song: SongSnap,
    caption: str,
    clip: ClipResult | None,
) -> bool:
    key = cache_key("clip", song.artist, song.title)
    file_id = get_file_id(key)
    if file_id:
        try:
            await message.answer_video(video=file_id, caption=caption, supports_streaming=True)
            return True
        except Exception:
            pass

    if not clip or not clip.path.exists():
        return False

    filename = _safe_filename(f"{song.artist} - {song.title}", "mp4")
    try:
        msg = await message.answer_video(
            video=FSInputFile(clip.path, filename=filename),
            caption=caption,
            duration=clip.duration,
            width=clip.width,
            height=clip.height,
            supports_streaming=True,
        )
        if msg.video and msg.video.file_id:
            set_file_id(clip.cache_key or key, msg.video.file_id)
        return True
    except Exception as exc:
        logger.warning("answer_video failed: %s", exc)
        try:
            await message.answer_document(
                document=FSInputFile(clip.path, filename=filename),
                caption=caption,
            )
            return True
        except Exception as exc2:
            logger.warning("clip document fallback failed: %s", exc2)
            return False


async def _deliver_lyrics(
    message: Message,
    song: SongSnap,
    caption: str,
    lang: str,
    lyrics: str | None,
) -> bool:
    if not lyrics:
        await message.answer(t(lang, "lyrics_not_found"))
        return False
    lyrics_service = LyricsService()
    footer = f"\n\n{caption}" if caption else ""
    text = lyrics_service.format_lyrics(song.artist, song.title, lyrics) + footer
    for chunk in lyrics_service.split_message(text):
        await message.answer(chunk)
    return True


async def _bg_send_audio(message: Message, bot: Bot, song: SongSnap, lang: str) -> None:
    """Tez yo‘l: kesh → preview (1–2s) → yo‘q bo‘lsa to‘liq yuklash."""
    try:
        caption = await _bot_caption(bot)
        key = cache_key("audio", song.artist, song.title)

        if get_file_id(key):
            await _deliver_audio(message, song, caption, None)
            return

        hit = cached_path(key)
        if hit:
            await _deliver_audio(
                message,
                song,
                caption,
                AudioResult(path=hit, title=song.title, artist=song.artist, cache_key=key, from_cache=True),
            )
            return

        # Tez: Deezer preview darhol
        preview_ok = await _send_preview(message, song, caption)
        # Keyingi bosish uchun to‘liq audioni fonda keshla (yubormaydi)
        _spawn(message.chat.id, "warm_audio", _warm_audio_cache(song))
        if preview_ok:
            return

        audio_result = await AudioService().download(song.artist, song.title)
        if await _deliver_audio(message, song, caption, audio_result):
            return
        await message.answer(
            f"❌ Audio yuklab bo‘lmadi.\n🎵 <b>{html.escape(song.artist)} – {html.escape(song.title)}</b>"
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("bg audio error: %s", exc)
        try:
            await message.answer("❌ Audio yuborishda xatolik.")
        except Exception:
            pass


class _Loading:
    """Ixcham loading: bitta xabar + Telegram chat action (edit spam yo‘q)."""

    __slots__ = ("status", "stop", "action_task")

    def __init__(self, status: Message):
        self.status = status
        self.stop = asyncio.Event()
        self.action_task: asyncio.Task | None = None

    @classmethod
    async def start(
        cls,
        message: Message,
        bot: Bot,
        text: str,
        action: ChatAction,
    ) -> "_Loading":
        status = await message.answer(f"{text}  ···")
        loader = cls(status)

        async def _actions() -> None:
            while not loader.stop.is_set():
                try:
                    await bot.send_chat_action(chat_id=message.chat.id, action=action)
                except Exception:
                    break
                try:
                    await asyncio.wait_for(loader.stop.wait(), timeout=4.0)
                    return
                except asyncio.TimeoutError:
                    continue

        loader.action_task = asyncio.create_task(_actions())
        return loader

    async def close(self) -> None:
        self.stop.set()
        if self.action_task and not self.action_task.done():
            self.action_task.cancel()
            try:
                await self.action_task
            except (asyncio.CancelledError, Exception):
                pass
        try:
            await self.status.delete()
        except Exception:
            pass


async def _bg_send_clip(message: Message, bot: Bot, song: SongSnap, lang: str = "uz") -> None:
    """Klipni Telegramga video sifatida yuborish."""
    loader: _Loading | None = None
    try:
        caption = await _bot_caption(bot)
        key = cache_key("clip", song.artist, song.title)

        if get_file_id(key):
            await _deliver_clip(message, song, caption, None)
            return

        hit = cached_path(key)
        if hit:
            ok = await _deliver_clip(
                message,
                song,
                caption,
                ClipResult(path=hit, title=song.title, cache_key=key, from_cache=True),
            )
            if ok:
                return

        loader = await _Loading.start(
            message, bot, t(lang, "loading_clip"), ChatAction.UPLOAD_VIDEO
        )
        clip = await ClipService().download(song.artist, song.title)
        await loader.close()
        loader = None

        if await _deliver_clip(message, song, caption, clip):
            return

        q = quote_plus(f"{song.artist} {song.title} official music video")
        url = song.video_url or f"https://www.youtube.com/results?search_query={q}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="▶️ YouTube’da ochish", url=url)]]
        )
        await message.answer(
            "⚠️ Klipni Telegramga yuklab bo‘lmadi.\nYouTube’dan tomosha qiling:",
            reply_markup=kb,
        )
    except asyncio.CancelledError:
        if loader:
            await loader.close()
        raise
    except Exception as exc:
        if loader:
            await loader.close()
        logger.warning("bg clip error: %s", exc)
        try:
            await message.answer("❌ Klip yuborishda xatolik.")
        except Exception:
            pass


async def _bg_send_lyrics(message: Message, bot: Bot, song: SongSnap, lang: str) -> None:
    loader: _Loading | None = None
    try:
        loader = await _Loading.start(
            message, bot, t(lang, "loading_lyrics"), ChatAction.TYPING
        )
        lyrics = await LyricsService().get_lyrics(song.artist, song.title)
        await loader.close()
        loader = None
        caption = await _bot_caption(bot)
        await _deliver_lyrics(message, song, caption, lang, lyrics)
    except asyncio.CancelledError:
        if loader:
            await loader.close()
        raise
    except Exception as exc:
        if loader:
            await loader.close()
        logger.warning("bg lyrics error: %s", exc)
        try:
            await message.answer(t(lang, "lyrics_not_found"))
        except Exception:
            pass


def _song_card_caption(song: SongSnap) -> str:
    title = html.escape(song.title or "—")
    artist = html.escape(song.artist or "—")
    album = html.escape(song.album or "—")
    duration = format_duration(song.duration)
    return (
        f"🎵 <b>{title}</b>\n"
        f"👤 {artist}\n"
        f"💿 {album}\n"
        f"⏱️ {duration}"
    )


async def _send_song_card(message: Message, song: SongSnap, lang: str) -> None:
    caption = _song_card_caption(song)
    kb = track_actions_keyboard(
        song_db_id=song.id,
        preview_url=song.preview_url,
        video_url=song.video_url,
        artist=song.artist,
        title=song.title,
        lang=lang,
    )

    sent = False
    if song.cover_url:
        try:
            await message.answer_photo(
                photo=song.cover_url,
                caption=caption,
                reply_markup=kb,
            )
            sent = True
        except Exception as exc:
            logger.warning("cover send via URL failed: %s", exc)
            cover_bytes = await _download_bytes(song.cover_url)
            if cover_bytes:
                try:
                    await message.answer_photo(
                        photo=BufferedInputFile(cover_bytes, filename="cover.jpg"),
                        caption=caption,
                        reply_markup=kb,
                    )
                    sent = True
                except Exception as exc2:
                    logger.warning("cover send via bytes failed: %s", exc2)

    if not sent:
        await message.answer(caption, reply_markup=kb)

    _song_snap_cache[song.id] = song
    # Faqat engil preview — yt-dlp warmup tarmoqni sekinlatmasin
    _spawn(message.chat.id, "warm_preview", _warm_preview_cache(song))


def _format_results_page(query: str, lines: list[str], page: int) -> str:
    start = page * PAGE_SIZE
    chunk = lines[start : start + PAGE_SIZE]
    body = "\n".join(f"{i}. {line}" for i, line in enumerate(chunk, start=1))
    return f"<b>{query}</b>\n\n{body}"


@router.message(F.text)
async def search_query(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Har qanday matn — qidiruv. /start qayta bosish shart emas."""
    query = (message.text or "").strip()
    if not query or query.startswith("/"):
        return

    lang = (await state.get_data()).get("lang") or await _user_lang(session, message.from_user.id)
    if len(query) < 2:
        await message.answer(t(lang, "min_chars"))
        return

    # Doim qidiruv holatida qolsin
    await state.set_state(SearchStates.waiting_query)

    status = await message.answer(t(lang, "searching"))

    settings = get_settings()
    music = MusicService(youtube_api_key=settings.youtube_api_key)
    tracks = await music.search(query, limit=8)

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


async def _resolve_snap(song_id: int, session: AsyncSession) -> SongSnap | None:
    snap = _song_snap_cache.get(song_id)
    if snap:
        return snap
    song = await SongRepository(session).get_by_id(song_id)
    if not song:
        return None
    snap = SongSnap.from_song(song)
    _song_snap_cache[song_id] = snap
    return snap


@router.callback_query(F.data.startswith("pick:"))
async def pick_result(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    await callback.answer()
    try:
        song_id = int((callback.data or "").split(":")[1])
    except (IndexError, ValueError):
        return
    if not callback.message:
        return
    snap = await _resolve_snap(song_id, session)
    if not snap:
        lang = await _user_lang(session, callback.from_user.id)
        await callback.message.answer(t(lang, "not_found"))
        return
    lang = (await _user_lang(session, callback.from_user.id)) if callback.from_user else "uz"
    _spawn(callback.message.chat.id, "card", _send_song_card(callback.message, snap, lang))


@router.callback_query(F.data.startswith("listen:"))
async def listen_callback(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    await callback.answer()  # tugma darhol “bosildi”
    try:
        song_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        return
    if not callback.message:
        return
    snap = await _resolve_snap(song_id, session)
    if not snap:
        return
    lang = await _user_lang(session, callback.from_user.id) if callback.from_user else "uz"
    _spawn(callback.message.chat.id, "audio", _bg_send_audio(callback.message, bot, snap, lang))


@router.callback_query(F.data.startswith("clip:"))
async def clip_callback(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    await callback.answer()
    try:
        song_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        return
    if not callback.message:
        return
    snap = await _resolve_snap(song_id, session)
    if not snap:
        return
    lang = await _user_lang(session, callback.from_user.id) if callback.from_user else "uz"
    _spawn(callback.message.chat.id, "clip", _bg_send_clip(callback.message, bot, snap, lang))


@router.callback_query(F.data.startswith("lyrics:"))
async def lyrics_callback(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    await callback.answer()
    try:
        song_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        return
    if not callback.message:
        return
    snap = await _resolve_snap(song_id, session)
    if not snap:
        return
    lang = await _user_lang(session, callback.from_user.id) if callback.from_user else "uz"
    _spawn(callback.message.chat.id, "lyrics", _bg_send_lyrics(callback.message, bot, snap, lang))
