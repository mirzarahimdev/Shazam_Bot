# MusicSave — Telegram Music Assistant

Telegram ichida musiqa qidirish, qo‘shiqni aniqlash, lyrics ko‘rish, rasmiy klip havolasini olish va o‘z videolarini saqlash uchun zamonaviy bot.

> **Muhim:** Bot noqonuniy yuklab olish yoki copyright himoyalangan kontentni ruxsatsiz tarqatish uchun mo‘ljallanmagan. Faqat ruxsat etilgan API va rasmiy manbalar ishlatiladi.

## Stack

- Python 3.12+
- aiogram 3.x
- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy 2.x + Alembic
- Redis
- Docker / Docker Compose

## Imkoniyatlar

| Bo‘lim | Tavsif |
|--------|--------|
| 🎵 Musiqa qidirish | Deezer / iTunes katalogi orqali qidiruv |
| 🎧 Qo‘shiqni aniqlash | AudD music recognition |
| 📝 Lyrics | lyrics.ovh API |
| 🎬 Klip | Rasmiy video havolasi (yuklab olish yo‘q) |
| 💾 Video Save | Telegram `file_id` orqali shaxsiy videolar |
| ⭐️ Sevimlilar | Song / artist / video |
| 👤 Profil / ⚙️ Sozlamalar | Til, bildirishnomalar, statistika |
| 🛠 Admin | Statistika, bloklash |

## Tezkor start (Docker)

```bash
cp .env.example .env
# .env ichida BOT_TOKEN, ADMIN_IDS, AUDD_API_TOKEN ni to‘ldiring

docker compose up -d --build
```

- API: http://localhost:8000/health  
- Docs: http://localhost:8000/docs  
- Bot polling avtomatik ishga tushadi

## Lokal o‘rnatish (Windows / PowerShell)

### 1. Virtual environment

```powershell
cd "c:\Users\The Darik\Desktop\tg Bot"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Python 3.12+ tavsiya etiladi (Docker image 3.12). Lokalda 3.14 ham ishlaydi.

### 2. `.env` sozlash

```powershell
Copy-Item .env.example .env
```

`.env` ni ochib to‘ldiring:

| O‘zgaruvchi | Qayerdan olish |
|-------------|----------------|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `ADMIN_IDS` | [@userinfobot](https://t.me/userinfobot) orqali Telegram ID |
| `AUDD_API_TOKEN` | [AudD Dashboard](https://dashboard.audd.io/) |
| `YOUTUBE_API_KEY` | Ixtiyoriy — [Google Cloud Console](https://console.cloud.google.com/) → YouTube Data API v3 |
| `WEBHOOK_SECRET` | Tasodifiy uzun string (admin API himoyasi) |
| `DATABASE_URL` | `postgresql+asyncpg://musicsave:musicsave@localhost:5432/musicsave` |
| `REDIS_URL` | `redis://localhost:6379/0` |

### 3. PostgreSQL va Redis

Docker orqali faqat infrastrukturani ishga tushirish:

```powershell
docker compose up -d db redis
```

### 4. Database migration

```powershell
alembic upgrade head
```

Yoki birinchi ishga tushirishda jadvallar `init_db()` orqali ham yaratiladi.

### 5. FastAPI server

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Bot

Yangi terminalda:

```powershell
.\.venv\Scripts\Activate.ps1
python -m app.bot.run
```

## API endpointlar

| Method | Path | Himoya |
|--------|------|--------|
| GET | `/health` | ochiq |
| GET | `/api/users` | admin |
| GET | `/api/users/{telegram_id}` | admin |
| POST | `/api/users/block` | admin |
| GET | `/api/songs` | ochiq |
| POST | `/api/search` | ochiq |
| POST | `/api/lyrics` | ochiq |
| GET | `/api/videos` | admin |
| POST | `/api/favorites` | ochiq |
| GET | `/api/favorites/{telegram_id}` | ochiq |
| GET | `/api/stats` | admin |

Admin so‘rovlari uchun headerlar:

```
X-Admin-Id: <telegram_id>
X-Admin-Secret: <WEBHOOK_SECRET>
```

## Admin bot buyruqlari

- `/admin` — panel
- `/block TELEGRAM_ID`
- `/unblock TELEGRAM_ID`

## Papka strukturasi

```
app/
├── bot/
│   ├── handlers/
│   ├── keyboards/
│   ├── middlewares/
│   ├── states/
│   └── run.py
├── api/
│   ├── routes/
│   └── dependencies/
├── database/
│   ├── models/
│   ├── repositories/
│   └── database.py
├── services/
├── config/
└── main.py
```

## Huquqiy eslatma

- Musiqa qidiruv: **Deezer** va **iTunes Search** (rasmiy katalog)
- Recognition: **AudD** (rasmiy API)
- Lyrics: **lyrics.ovh** (API shartlariga rioya qiling)
- Kliplar: faqat **rasmiy URL** — serverga video yuklab Telegramga qayta yuklanmaydi
- Video Save: faqat foydalanuvchining **o‘z** videolari, Telegram `file_id` orqali

## Muammolarni bartaraf etish

**`BOT_TOKEN` xato** — BotFather dan yangi token oling.  
**AudD ishlamayapti** — `AUDD_API_TOKEN` to‘g‘riligini va limitni tekshiring.  
**DB ulanmayapti** — `docker compose ps` va `DATABASE_URL` ni tekshiring.  
**Redis yo‘q** — rate limit o‘chiriladi, bot ishlashda davom etadi.

## Litsenziya

O‘quv / shaxsiy loyiha. Tashqi API litsenziyalariga alohida rioya qiling.
