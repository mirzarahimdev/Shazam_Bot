from typing import Any

LANG_UZ = "uz"
LANG_UZ_CYRL = "uz_cyrl"
LANG_RU = "ru"
LANG_EN = "en"

SUPPORTED_LANGS = {LANG_UZ, LANG_UZ_CYRL, LANG_RU, LANG_EN}

LANGUAGE_PROMPT = (
    "O'zingizga qulay tilni tanlang 🇺🇿\n\n"
    "Ўзингизга қулай тилни танланг 🇺🇿\n\n"
    "Выбери язык, который тебе нравится 🇷🇺\n\n"
    "Choose the language you like 🇺🇸"
)

TEXTS: dict[str, dict[str, str]] = {
    LANG_UZ: {
        "welcome": (
            "🎵 Salom! Botga xush kelibsiz.\n\n"
            "Bu yerda:\n"
            "🎵 Musiqa\n"
            "🎬 Video klip\n"
            "📝 Qo‘shiq so‘zlari\n"
            "topishingiz mumkin."
        ),
        "help": (
            "Yordam:\n"
            "• 🎵 Musiqa — qo‘shiq/ijrochi nomini yuboring\n"
            "• 🎬 Video klip — rasmiy klipni topish\n"
            "• 📝 Qo‘shiq so‘zlari — lyrics ko‘rish"
        ),
        "btn_music": "🎵 Musiqa",
        "btn_clip": "🎬 Video klip",
        "btn_lyrics": "📝 Qo‘shiq so‘zlari",
        "btn_back": "🏠 Menyuga qaytish",
        "menu": "Asosiy menyu:",
        "ask_music": "🔍 Qo‘shiq yoki ijrochi nomini yuboring.\nMasalan: <code>Imagine Dragons Believer</code>",
        "ask_clip": "🎬 Klip uchun qo‘shiq yoki ijrochi nomini yuboring.",
        "ask_lyrics": "📝 So‘zlar uchun qo‘shiq yoki ijrochi nomini yuboring.",
        "searching": "🔎 Qidirilmoqda...",
        "not_found": "❌ Natija topilmadi. Boshqa so‘rov yuboring.",
        "min_chars": "Kamida 2 ta belgi yuboring.",
        "lyrics_not_found": "❌ Bu qo‘shiq uchun so‘zlar topilmadi.",
        "clip_caption": "🎬 <b>Official Music Video</b>\n\n🎵 {title}\n",
        "clip_note": "\nCopyright himoyalangan videolar yuklab olinmaydi — faqat rasmiy havola beriladi.",
        "listen": "🎧 Tinglash",
        "clip": "🎬 Klip",
        "lyrics": "📝 So‘zlar",
        "watch": "▶️ Tomosha qilish",
        "lang_saved": "✅ Til saqlandi: O'zbekcha\n\n🔍 Qo‘shiq nomini yozing:",
        "ask_song": "🔍 Qo‘shiq nomini yozing:",
        "loading_clip": "🎬  <i>yuklanmoqda</i>",
        "loading_lyrics": "📝  <i>yuklanmoqda</i>",
    },
    LANG_UZ_CYRL: {
        "welcome": (
            "🎵 Салом! Ботга хуш келибсиз.\n\n"
            "Бу ерда:\n"
            "🎵 Мусиқа\n"
            "🎬 Видео клип\n"
            "📝 Қўшиқ сўзлари\n"
            "топишингиз мумкин."
        ),
        "help": (
            "Ёрдам:\n"
            "• 🎵 Мусиқа — қўшиқ/ижрочи номини юборинг\n"
            "• 🎬 Видео клип — расмий клипни топиш\n"
            "• 📝 Қўшиқ сўзлари — lyrics кўриш"
        ),
        "btn_music": "🎵 Мусиқа",
        "btn_clip": "🎬 Видео клип",
        "btn_lyrics": "📝 Қўшиқ сўзлари",
        "btn_back": "🏠 Менюга қайтиш",
        "menu": "Асосий меню:",
        "ask_music": "🔍 Қўшиқ ёки ижрочи номини юборинг.\nМасалан: <code>Imagine Dragons Believer</code>",
        "ask_clip": "🎬 Клип учун қўшиқ ёки ижрочи номини юборинг.",
        "ask_lyrics": "📝 Сўзлар учун қўшиқ ёки ижрочи номини юборинг.",
        "searching": "🔎 Қидирилмоқда...",
        "not_found": "❌ Натижа топилмади. Бошқа сўров юборинг.",
        "min_chars": "Камида 2 та белги юборинг.",
        "lyrics_not_found": "❌ Бу қўшиқ учун сўзлар топилмади.",
        "clip_caption": "🎬 <b>Official Music Video</b>\n\n🎵 {title}\n",
        "clip_note": "\nCopyright ҳимояланган видеолар юклаб олинмайди — фақат расмий ҳавола берилади.",
        "listen": "🎧 Тинглаш",
        "clip": "🎬 Клип",
        "lyrics": "📝 Сўзлар",
        "watch": "▶️ Томоша қилиш",
        "lang_saved": "✅ Тил сақланди: Ўзбекча\n\n🔍 Қўшиқ номини ёзинг:",
        "ask_song": "🔍 Қўшиқ номини ёзинг:",
        "loading_clip": "🎬  <i>юкланмоқда</i>",
        "loading_lyrics": "📝  <i>юкланмоқда</i>",
    },
    LANG_RU: {
        "welcome": (
            "🎵 Привет! Добро пожаловать в бота.\n\n"
            "Здесь можно найти:\n"
            "🎵 Музыку\n"
            "🎬 Видеоклип\n"
            "📝 Текст песни"
        ),
        "help": (
            "Помощь:\n"
            "• 🎵 Музыка — отправьте название песни/исполнителя\n"
            "• 🎬 Видеоклип — найти официальный клип\n"
            "• 📝 Текст песни — показать lyrics"
        ),
        "btn_music": "🎵 Музыка",
        "btn_clip": "🎬 Видеоклип",
        "btn_lyrics": "📝 Текст песни",
        "btn_back": "🏠 В меню",
        "menu": "Главное меню:",
        "ask_music": "🔍 Отправьте название песни или исполнителя.\nНапример: <code>Imagine Dragons Believer</code>",
        "ask_clip": "🎬 Отправьте название песни или исполнителя для клипа.",
        "ask_lyrics": "📝 Отправьте название песни или исполнителя для текста.",
        "searching": "🔎 Ищу...",
        "not_found": "❌ Ничего не найдено. Попробуйте другой запрос.",
        "min_chars": "Отправьте минимум 2 символа.",
        "lyrics_not_found": "❌ Текст для этой песни не найден.",
        "clip_caption": "🎬 <b>Official Music Video</b>\n\n🎵 {title}\n",
        "clip_note": "\nЗащищённые авторским правом видео не скачиваются — только официальная ссылка.",
        "listen": "🎧 Слушать",
        "clip": "🎬 Клип",
        "lyrics": "📝 Текст",
        "watch": "▶️ Смотреть",
        "lang_saved": "✅ Язык сохранён: Русский\n\n🔍 Напишите название песни:",
        "ask_song": "🔍 Напишите название песни:",
        "loading_clip": "🎬  <i>загрузка</i>",
        "loading_lyrics": "📝  <i>загрузка</i>",
    },
    LANG_EN: {
        "welcome": (
            "🎵 Hi! Welcome to the bot.\n\n"
            "Here you can find:\n"
            "🎵 Music\n"
            "🎬 Music video\n"
            "📝 Lyrics"
        ),
        "help": (
            "Help:\n"
            "• 🎵 Music — send a song/artist name\n"
            "• 🎬 Music video — find the official clip\n"
            "• 📝 Lyrics — show song lyrics"
        ),
        "btn_music": "🎵 Music",
        "btn_clip": "🎬 Music video",
        "btn_lyrics": "📝 Lyrics",
        "btn_back": "🏠 Back to menu",
        "menu": "Main menu:",
        "ask_music": "🔍 Send a song or artist name.\nExample: <code>Imagine Dragons Believer</code>",
        "ask_clip": "🎬 Send a song or artist name to find the official clip.",
        "ask_lyrics": "📝 Send a song or artist name to get lyrics.",
        "searching": "🔎 Searching...",
        "not_found": "❌ No results. Try another query.",
        "min_chars": "Please send at least 2 characters.",
        "lyrics_not_found": "❌ Lyrics not found for this song.",
        "clip_caption": "🎬 <b>Official Music Video</b>\n\n🎵 {title}\n",
        "clip_note": "\nCopyrighted videos are not downloaded — only the official link is provided.",
        "listen": "🎧 Listen",
        "clip": "🎬 Clip",
        "lyrics": "📝 Lyrics",
        "watch": "▶️ Watch",
        "lang_saved": "✅ Language saved: English\n\n🔍 Type a song name:",
        "ask_song": "🔍 Type a song name:",
        "loading_clip": "🎬  <i>loading</i>",
        "loading_lyrics": "📝  <i>loading</i>",
    },
}


def t(lang: str | None, key: str, **kwargs: Any) -> str:
    pack = TEXTS.get(lang or LANG_UZ) or TEXTS[LANG_UZ]
    text = pack.get(key) or TEXTS[LANG_UZ].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def all_menu_buttons() -> set[str]:
    buttons: set[str] = set()
    for lang in TEXTS.values():
        buttons.add(lang["btn_music"])
        buttons.add(lang["btn_clip"])
        buttons.add(lang["btn_lyrics"])
        buttons.add(lang["btn_back"])
    return buttons


def button_action(text: str) -> str | None:
    for lang_code, pack in TEXTS.items():
        if text == pack["btn_music"]:
            return "music"
        if text == pack["btn_clip"]:
            return "clip"
        if text == pack["btn_lyrics"]:
            return "lyrics"
        if text == pack["btn_back"]:
            return "back"
    return None
