from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.bot.i18n import t

PAGE_SIZE = 10


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
                InlineKeyboardButton(text="🇺🇿 Ўзбекча", callback_data="lang:uz_cyrl"),
            ],
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇺🇸 English", callback_data="lang:en"),
            ],
        ]
    )


def main_menu_keyboard(lang: str = "uz") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_music"))],
            [
                KeyboardButton(text=t(lang, "btn_clip")),
                KeyboardButton(text=t(lang, "btn_lyrics")),
            ],
        ],
        resize_keyboard=True,
    )


def search_results_keyboard(*, page: int, song_ids: list[int]) -> InlineKeyboardMarkup:
    """Number buttons 1..N for current page; callback carries real song_id."""
    total = len(song_ids)
    start = page * PAGE_SIZE
    page_ids = song_ids[start : start + PAGE_SIZE]
    count = len(page_ids)

    rows: list[list[InlineKeyboardButton]] = []
    row1 = [
        InlineKeyboardButton(text=str(i + 1), callback_data=f"pick:{page_ids[i]}")
        for i in range(min(5, count))
    ]
    if row1:
        rows.append(row1)
    if count > 5:
        row2 = [
            InlineKeyboardButton(text=str(i + 1), callback_data=f"pick:{page_ids[i]}")
            for i in range(5, count)
        ]
        rows.append(row2)

    nav: list[InlineKeyboardButton] = []
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅", callback_data=f"page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡", callback_data=f"page:{page + 1}"))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def track_actions_keyboard(
    *,
    song_db_id: int,
    preview_url: str | None = None,
    video_url: str | None = None,
    artist: str = "",
    title: str = "",
    lang: str = "uz",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "clip"), callback_data=f"clip:{song_db_id}"),
                InlineKeyboardButton(text=t(lang, "lyrics"), callback_data=f"lyrics:{song_db_id}"),
            ]
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


def clip_keyboard(url: str, lang: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "watch"), url=url)]]
    )
