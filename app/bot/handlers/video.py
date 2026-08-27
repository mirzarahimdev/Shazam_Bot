from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.constants import MENU_BUTTONS
from app.bot.keyboards import (
    category_pick_keyboard,
    main_menu_keyboard,
    saved_video_actions_keyboard,
    video_categories_keyboard,
    video_save_menu_keyboard,
)
from app.bot.states import VideoStates
from app.config import get_settings
from app.database.repositories import SavedVideoRepository, UserRepository
from app.services.video_service import VideoService

router = Router(name="video")


@router.message(F.text == "💾 Video Save")
async def video_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "💾 <b>Video Save</b>\n\n"
        "O‘z videolaringizni Telegram file_id orqali saqlang.\n"
        "Copyright himoyalangan kontentni ruxsatsiz yuklab olish qo‘llab-quvvatlanmaydi.",
        reply_markup=video_save_menu_keyboard(),
    )


@router.callback_query(F.data == "video:menu")
async def video_menu_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "💾 <b>Video Save</b>",
        reply_markup=video_save_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "video:upload")
async def video_upload_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(VideoStates.waiting_video)
    await callback.message.answer("📤 Saqlash uchun video yuboring.")
    await callback.answer()


@router.message(VideoStates.waiting_video, F.video)
async def receive_video(message: Message, state: FSMContext) -> None:
    settings = get_settings()
    video = message.video
    if not VideoService.validate_size(video.file_size, settings.max_media_size_bytes):
        await message.answer(f"❌ Fayl juda katta. Max: {settings.max_media_size_mb} MB")
        return
    if not VideoService.validate_mime(video.mime_type):
        await message.answer("❌ Bu video formati qo‘llab-quvvatlanmaydi.")
        return

    await state.update_data(
        pending_video={
            "telegram_file_id": video.file_id,
            "telegram_file_unique_id": video.file_unique_id,
            "file_name": video.file_name,
            "file_size": video.file_size,
            "mime_type": video.mime_type,
            "duration": video.duration,
            "caption": message.caption,
        }
    )
    await state.set_state(VideoStates.waiting_category)
    await message.answer("📂 Kategoriya tanlang:", reply_markup=category_pick_keyboard())


@router.callback_query(VideoStates.waiting_category, F.data.startswith("video:setcat:"))
async def set_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    category = callback.data.split(":")[-1]
    data = await state.get_data()
    pending = data.get("pending_video")
    if not pending:
        await callback.answer("Video topilmadi", show_alert=True)
        return

    user_repo = UserRepository(session)
    user, _ = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    video = await SavedVideoRepository(session).add(
        user_id=user.id,
        category=category,
        **pending,
    )
    await state.clear()
    label = VideoService.category_label(category)
    await callback.message.answer(
        f"✅ Video saqlandi!\n📂 {label}\n🆔 #{video.id}",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


async def _ensure_user(session: AsyncSession, tg_user) -> object:
    repo = UserRepository(session)
    user, _ = await repo.get_or_create(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
    )
    return user


async def _send_video_list(
    callback: CallbackQuery,
    session: AsyncSession,
    *,
    category: str | None = None,
    favorites_only: bool = False,
    query: str | None = None,
) -> None:
    user = await _ensure_user(session, callback.from_user)
    videos = await SavedVideoRepository(session).list_by_user(
        user.id,
        category=category,
        favorites_only=favorites_only,
        query=query,
        limit=10,
    )
    if not videos:
        await callback.message.answer("📭 Videolar topilmadi.")
        await callback.answer()
        return

    for v in videos:
        caption = (
            f"🆔 #{v.id}\n"
            f"📂 {VideoService.category_label(v.category)}\n"
            f"📝 {v.caption or '—'}"
        )
        await callback.message.answer_video(
            v.telegram_file_id,
            caption=caption,
            reply_markup=saved_video_actions_keyboard(v.id, v.is_favorite),
        )
    await callback.answer()


@router.callback_query(F.data == "video:list")
async def list_videos(callback: CallbackQuery, session: AsyncSession) -> None:
    await _send_video_list(callback, session)


@router.callback_query(F.data == "video:favorites")
async def list_fav_videos(callback: CallbackQuery, session: AsyncSession) -> None:
    await _send_video_list(callback, session, favorites_only=True)


@router.callback_query(F.data == "video:categories")
async def categories_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📂 Kategoriyani tanlang:",
        reply_markup=video_categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("video:cat:"))
async def list_by_category(callback: CallbackQuery, session: AsyncSession) -> None:
    category = callback.data.split(":")[-1]
    await _send_video_list(callback, session, category=category)


@router.callback_query(F.data == "video:search")
async def video_search_entry(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(VideoStates.waiting_search)
    await callback.message.answer("🔎 Qidiruv matnini yuboring (caption yoki fayl nomi):")
    await callback.answer()


@router.message(VideoStates.waiting_search, F.text, ~F.text.in_(MENU_BUTTONS))
async def video_search(message: Message, state: FSMContext, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    user = await _ensure_user(session, message.from_user)
    videos = await SavedVideoRepository(session).list_by_user(user.id, query=query, limit=10)
    await state.clear()
    if not videos:
        await message.answer("📭 Hech narsa topilmadi.")
        return
    for v in videos:
        await message.answer_video(
            v.telegram_file_id,
            caption=f"🆔 #{v.id}\n📝 {v.caption or '—'}",
            reply_markup=saved_video_actions_keyboard(v.id, v.is_favorite),
        )


@router.callback_query(F.data.startswith("video:resend:"))
async def resend_video(callback: CallbackQuery, session: AsyncSession) -> None:
    video_id = int(callback.data.split(":")[-1])
    user = await _ensure_user(session, callback.from_user)
    video = await SavedVideoRepository(session).get_by_id(video_id, user.id)
    if not video:
        await callback.answer("Topilmadi", show_alert=True)
        return
    await callback.message.answer_video(video.telegram_file_id, caption=video.caption)
    await callback.answer("📤 Yuborildi")


@router.callback_query(F.data.startswith("video:fav:"))
async def toggle_video_fav(callback: CallbackQuery, session: AsyncSession) -> None:
    video_id = int(callback.data.split(":")[-1])
    user = await _ensure_user(session, callback.from_user)
    result = await SavedVideoRepository(session).toggle_favorite(video_id, user.id)
    if result is None:
        await callback.answer("Topilmadi", show_alert=True)
        return
    await callback.answer("⭐️ Yangilandi" if result else "Sevimlidan olib tashlandi")


@router.callback_query(F.data.startswith("video:del:"))
async def delete_video(callback: CallbackQuery, session: AsyncSession) -> None:
    video_id = int(callback.data.split(":")[-1])
    user = await _ensure_user(session, callback.from_user)
    ok = await SavedVideoRepository(session).delete(video_id, user.id)
    if ok:
        await callback.message.answer(f"🗑 Video #{video_id} o‘chirildi.")
        await callback.answer("O‘chirildi")
    else:
        await callback.answer("Topilmadi", show_alert=True)
