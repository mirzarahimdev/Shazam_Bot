from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_admin
from app.database.repositories import (
    FavoriteRepository,
    RecognizedSongRepository,
    SavedVideoRepository,
    SearchHistoryRepository,
    StatsRepository,
    UserRepository,
)
from app.services.lyrics_service import LyricsService
from app.services.music_service import MusicService
from app.config import get_settings

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)


class LyricsRequest(BaseModel):
    artist: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)


class FavoriteRequest(BaseModel):
    telegram_id: int
    item_type: str = Field(pattern="^(song|artist|video)$")
    item_id: str = Field(min_length=1, max_length=100)
    title: str | None = None


class BlockRequest(BaseModel):
    telegram_id: int
    blocked: bool = True


@router.get("/users")
async def list_users_count(
    session: AsyncSession = Depends(get_db),
    _: int = Depends(verify_admin),
) -> dict:
    count = await UserRepository(session).count_all()
    return {"users_count": count}


@router.get("/users/{telegram_id}")
async def get_user(
    telegram_id: int,
    session: AsyncSession = Depends(get_db),
    _: int = Depends(verify_admin),
) -> dict:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "language": user.language,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at,
    }


@router.post("/users/block")
async def block_user(
    body: BlockRequest,
    session: AsyncSession = Depends(get_db),
    _: int = Depends(verify_admin),
) -> dict:
    ok = await UserRepository(session).set_blocked(body.telegram_id, body.blocked)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "blocked": body.blocked}


@router.get("/songs")
async def songs_info() -> dict:
    return {
        "provider": "deezer/itunes",
        "note": "Search via POST /api/search",
    }


@router.post("/search")
async def search_songs(body: SearchRequest) -> dict:
    settings = get_settings()
    music = MusicService(youtube_api_key=settings.youtube_api_key)
    tracks = await music.search(body.query, limit=10)
    return {
        "query": body.query,
        "count": len(tracks),
        "results": [track.__dict__ for track in tracks],
    }


@router.post("/recognize")
async def recognize_info() -> dict:
    return {
        "status": "use_telegram_bot",
        "note": "Recognition requires media upload via Telegram bot (AudD).",
    }


@router.post("/lyrics")
async def get_lyrics(body: LyricsRequest) -> dict:
    lyrics = await LyricsService().get_lyrics(body.artist, body.title)
    if not lyrics:
        raise HTTPException(status_code=404, detail="Lyrics not found")
    return {"artist": body.artist, "title": body.title, "lyrics": lyrics}


@router.get("/videos")
async def videos_count(
    session: AsyncSession = Depends(get_db),
    _: int = Depends(verify_admin),
) -> dict:
    return {"saved_videos": await SavedVideoRepository(session).count_all()}


@router.get("/videos/{telegram_id}")
async def user_videos(
    telegram_id: int,
    session: AsyncSession = Depends(get_db),
    _: int = Depends(verify_admin),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    videos = await SavedVideoRepository(session).list_by_user(user.id, limit=limit)
    return {
        "items": [
            {
                "id": v.id,
                "category": v.category,
                "caption": v.caption,
                "file_unique_id": v.telegram_file_unique_id,
                "created_at": v.created_at,
            }
            for v in videos
        ]
    }


@router.post("/favorites")
async def add_favorite(
    body: FavoriteRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    user = await UserRepository(session).get_by_telegram_id(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    fav, created = await FavoriteRepository(session).add(
        user_id=user.id,
        item_type=body.item_type,
        item_id=body.item_id,
        title=body.title,
    )
    return {"id": fav.id, "created": created}


@router.get("/favorites/{telegram_id}")
async def list_favorites(
    telegram_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    user = await UserRepository(session).get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    items = await FavoriteRepository(session).list_by_user(user.id)
    return {
        "items": [
            {
                "id": i.id,
                "item_type": i.item_type,
                "item_id": i.item_id,
                "title": i.title,
                "created_at": i.created_at,
            }
            for i in items
        ]
    }


@router.get("/stats")
async def stats(
    session: AsyncSession = Depends(get_db),
    _: int = Depends(verify_admin),
) -> dict:
    users = await UserRepository(session).count_all()
    videos = await SavedVideoRepository(session).count_all()
    period = await StatsRepository(session).daily_weekly()
    top_search = await SearchHistoryRepository(session).top_queries(10)
    top_recog = await RecognizedSongRepository(session).top_songs(10)
    return {
        "users": users,
        "videos": videos,
        "period": period,
        "top_searches": [{"query": q, "count": c} for q, c in top_search],
        "top_recognized": [
            {"title": t, "artist": a, "count": c} for t, a, c in top_recog
        ],
    }
