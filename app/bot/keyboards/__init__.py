from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.services.video_service import VIDEO_CATEGORIES


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎵 Musiqa qidirish"), KeyboardButton(text="🎧 Qo‘shiqni aniqlash")],
            [KeyboardButton(text="💾 Video Save"), KeyboardButton(text="⭐️ Sevimlilar")],
            [KeyboardButton(text="👤 Profil"), KeyboardButton(text="⚙️ Sozlamalar")],
        ],
        resize_keyboard=True,
    )


def track_actions_keyboard(
    *,
    song_db_id: int,
    preview_url: str | None,
    video_url: str | None,
    artist: str,
    title: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    listen_row: list[InlineKeyboardButton] = []
    if preview_url:
        listen_row.append(InlineKeyboardButton(text="🎧 Tinglash", url=preview_url))
    else:
        listen_row.append(
            InlineKeyboardButton(text="🎧 Tinglash", callback_data=f"listen:{song_db_id}")
        )
    rows.append(listen_row)

    rows.append(
        [
            InlineKeyboardButton(text="🎬 Klip", callback_data=f"clip:{song_db_id}"),
            InlineKeyboardButton(text="📝 Lyrics", callback_data=f"lyrics:{song_db_id}"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="⭐️ Sevimlilarga qo‘shish",
                callback_data=f"fav:song:{song_db_id}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def recognition_actions_keyboard(
    *,
    title: str,
    artist: str,
    source_url: str | None,
    video_url: str | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if source_url:
        rows.append([InlineKeyboardButton(text="🎧 Rasmiy manba", url=source_url)])
    if video_url:
        rows.append([InlineKeyboardButton(text="🎬 Official video", url=video_url)])
    rows.append(
        [
            InlineKeyboardButton(
                text="📝 Lyrics",
                callback_data=f"lyrics_text:{artist[:40]}|{title[:40]}",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="⭐️ Sevimlilarga qo‘shish",
                callback_data=f"fav:artist:{artist[:60]}",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def video_save_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Video yuborish", callback_data="video:upload")],
            [InlineKeyboardButton(text="📁 Mening videolarim", callback_data="video:list")],
            [
                InlineKeyboardButton(text="📂 Kategoriyalar", callback_data="video:categories"),
                InlineKeyboardButton(text="🔎 Qidirish", callback_data="video:search"),
            ],
            [InlineKeyboardButton(text="⭐️ Sevimlilar", callback_data="video:favorites")],
        ]
    )


def video_categories_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    items = list(VIDEO_CATEGORIES.items())
    for i in range(0, len(items), 2):
        chunk = items[i : i + 2]
        rows.append(
            [
                InlineKeyboardButton(text=label, callback_data=f"video:cat:{key}")
                for key, label in chunk
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="video:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_pick_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    items = list(VIDEO_CATEGORIES.items())
    for i in range(0, len(items), 2):
        chunk = items[i : i + 2]
        rows.append(
            [
                InlineKeyboardButton(text=label, callback_data=f"video:setcat:{key}")
                for key, label in chunk
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def saved_video_actions_keyboard(video_id: int, is_favorite: bool) -> InlineKeyboardMarkup:
    fav_text = "⭐️ Sevimlidan olib tashlash" if is_favorite else "⭐️ Sevimlilarga"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📤 Qayta yuborish", callback_data=f"video:resend:{video_id}"),
                InlineKeyboardButton(text=fav_text, callback_data=f"video:fav:{video_id}"),
            ],
            [InlineKeyboardButton(text="🗑 O‘chirish", callback_data=f"video:del:{video_id}")],
        ]
    )


def settings_keyboard(language: str, notifications: bool) -> InlineKeyboardMarkup:
    notif = "🔔 Yoqilgan" if notifications else "🔕 O‘chirilgan"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O‘zbek", callback_data="settings:lang:uz"),
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="settings:lang:ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="settings:lang:en"),
            ],
            [InlineKeyboardButton(text=f"Bildirishnomalar: {notif}", callback_data="settings:notif")],
            [InlineKeyboardButton(text=f"Joriy til: {language.upper()}", callback_data="settings:noop")],
        ]
    )


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats")],
            [InlineKeyboardButton(text="🎵 Top qidiruvlar", callback_data="admin:top_search")],
            [InlineKeyboardButton(text="🎧 Top aniqlashlar", callback_data="admin:top_recog")],
        ]
    )


def clip_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="▶️ Tomosha qilish", url=url)]]
    )
