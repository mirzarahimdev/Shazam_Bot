from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Favorite,
    RecognizedSong,
    SavedVideo,
    SearchHistory,
    Settings,
    Song,
    User,
)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language: str = "uz",
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.updated_at = datetime.now(timezone.utc)
            await self.session.flush()
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=language,
        )
        self.session.add(user)
        await self.session.flush()

        settings = Settings(user_id=user.id, language=language)
        self.session.add(settings)
        await self.session.flush()
        return user, True

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return int(result.scalar_one())

    async def set_blocked(self, telegram_id: int, blocked: bool) -> bool:
        result = await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_blocked=blocked)
            .returning(User.id)
        )
        return result.scalar_one_or_none() is not None

    async def is_blocked(self, telegram_id: int) -> bool:
        user = await self.get_by_telegram_id(telegram_id)
        return bool(user and user.is_blocked)


class SongRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(
        self,
        *,
        external_id: Optional[str],
        title: str,
        artist: str,
        album: Optional[str] = None,
        cover_url: Optional[str] = None,
        duration: Optional[int] = None,
        preview_url: Optional[str] = None,
        source_url: Optional[str] = None,
        video_url: Optional[str] = None,
        provider: str = "deezer",
    ) -> Song:
        song = None
        if external_id:
            result = await self.session.execute(
                select(Song).where(Song.external_id == external_id, Song.provider == provider)
            )
            song = result.scalar_one_or_none()

        if song:
            song.title = title
            song.artist = artist
            song.album = album
            song.cover_url = cover_url
            song.duration = duration
            song.preview_url = preview_url
            song.source_url = source_url
            song.video_url = video_url
        else:
            song = Song(
                external_id=external_id,
                title=title,
                artist=artist,
                album=album,
                cover_url=cover_url,
                duration=duration,
                preview_url=preview_url,
                source_url=source_url,
                video_url=video_url,
                provider=provider,
            )
            self.session.add(song)

        await self.session.flush()
        return song

    async def get_by_id(self, song_id: int) -> Optional[Song]:
        result = await self.session.execute(select(Song).where(Song.id == song_id))
        return result.scalar_one_or_none()


class SearchHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, query: str, results_count: int) -> SearchHistory:
        item = SearchHistory(user_id=user_id, query=query, results_count=results_count)
        self.session.add(item)
        await self.session.flush()
        return item

    async def count_by_user(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(SearchHistory.id)).where(SearchHistory.user_id == user_id)
        )
        return int(result.scalar_one())

    async def top_queries(self, limit: int = 10) -> Sequence[tuple[str, int]]:
        result = await self.session.execute(
            select(SearchHistory.query, func.count(SearchHistory.id).label("cnt"))
            .group_by(SearchHistory.query)
            .order_by(func.count(SearchHistory.id).desc())
            .limit(limit)
        )
        return result.all()


class RecognizedSongRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        user_id: int,
        title: str,
        artist: str,
        album: Optional[str] = None,
        cover_url: Optional[str] = None,
        source_url: Optional[str] = None,
        video_url: Optional[str] = None,
        song_id: Optional[int] = None,
    ) -> RecognizedSong:
        item = RecognizedSong(
            user_id=user_id,
            song_id=song_id,
            title=title,
            artist=artist,
            album=album,
            cover_url=cover_url,
            source_url=source_url,
            video_url=video_url,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def count_by_user(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(RecognizedSong.id)).where(RecognizedSong.user_id == user_id)
        )
        return int(result.scalar_one())

    async def top_songs(self, limit: int = 10) -> Sequence[tuple[str, str, int]]:
        result = await self.session.execute(
            select(
                RecognizedSong.title,
                RecognizedSong.artist,
                func.count(RecognizedSong.id).label("cnt"),
            )
            .group_by(RecognizedSong.title, RecognizedSong.artist)
            .order_by(func.count(RecognizedSong.id).desc())
            .limit(limit)
        )
        return result.all()


class SavedVideoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        *,
        user_id: int,
        telegram_file_id: str,
        telegram_file_unique_id: str,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None,
        duration: Optional[int] = None,
        caption: Optional[str] = None,
        category: str = "other",
    ) -> SavedVideo:
        video = SavedVideo(
            user_id=user_id,
            telegram_file_id=telegram_file_id,
            telegram_file_unique_id=telegram_file_unique_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            duration=duration,
            caption=caption,
            category=category,
        )
        self.session.add(video)
        await self.session.flush()
        return video

    async def list_by_user(
        self,
        user_id: int,
        *,
        category: Optional[str] = None,
        favorites_only: bool = False,
        query: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[SavedVideo]:
        stmt = select(SavedVideo).where(SavedVideo.user_id == user_id)
        if category:
            stmt = stmt.where(SavedVideo.category == category)
        if favorites_only:
            stmt = stmt.where(SavedVideo.is_favorite.is_(True))
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                (SavedVideo.caption.ilike(like)) | (SavedVideo.file_name.ilike(like))
            )
        stmt = stmt.order_by(SavedVideo.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, video_id: int, user_id: int) -> Optional[SavedVideo]:
        result = await self.session.execute(
            select(SavedVideo).where(SavedVideo.id == video_id, SavedVideo.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, video_id: int, user_id: int) -> bool:
        video = await self.get_by_id(video_id, user_id)
        if not video:
            return False
        await self.session.delete(video)
        await self.session.flush()
        return True

    async def toggle_favorite(self, video_id: int, user_id: int) -> Optional[bool]:
        video = await self.get_by_id(video_id, user_id)
        if not video:
            return None
        video.is_favorite = not video.is_favorite
        await self.session.flush()
        return video.is_favorite

    async def count_by_user(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(SavedVideo.id)).where(SavedVideo.user_id == user_id)
        )
        return int(result.scalar_one())

    async def count_all(self) -> int:
        result = await self.session.execute(select(func.count(SavedVideo.id)))
        return int(result.scalar_one())


class FavoriteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self,
        user_id: int,
        item_type: str,
        item_id: str,
        title: Optional[str] = None,
        extra_data: Optional[str] = None,
    ) -> tuple[Favorite, bool]:
        result = await self.session.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.item_type == item_type,
                Favorite.item_id == item_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing, False

        fav = Favorite(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            title=title,
            extra_data=extra_data,
        )
        self.session.add(fav)
        await self.session.flush()
        return fav, True

    async def list_by_user(self, user_id: int, limit: int = 50) -> Sequence[Favorite]:
        result = await self.session.execute(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def remove(self, user_id: int, item_type: str, item_id: str) -> bool:
        result = await self.session.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.item_type == item_type,
                Favorite.item_id == item_id,
            )
        )
        fav = result.scalar_one_or_none()
        if not fav:
            return False
        await self.session.delete(fav)
        await self.session.flush()
        return True

    async def count_by_user(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
        )
        return int(result.scalar_one())


class SettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user(self, user_id: int) -> Optional[Settings]:
        result = await self.session.execute(
            select(Settings).where(Settings.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_language(self, user_id: int, language: str) -> Settings:
        settings = await self.get_by_user(user_id)
        if not settings:
            settings = Settings(user_id=user_id, language=language)
            self.session.add(settings)
        else:
            settings.language = language
        await self.session.flush()
        return settings

    async def toggle_notifications(self, user_id: int) -> Settings:
        settings = await self.get_by_user(user_id)
        if not settings:
            settings = Settings(user_id=user_id, notifications_enabled=True)
            self.session.add(settings)
        else:
            settings.notifications_enabled = not settings.notifications_enabled
        await self.session.flush()
        return settings


class StatsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def daily_weekly(self) -> dict:
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        users_day = await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= day_ago)
        )
        users_week = await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )
        searches_day = await self.session.execute(
            select(func.count(SearchHistory.id)).where(SearchHistory.created_at >= day_ago)
        )
        searches_week = await self.session.execute(
            select(func.count(SearchHistory.id)).where(SearchHistory.created_at >= week_ago)
        )
        recognized_day = await self.session.execute(
            select(func.count(RecognizedSong.id)).where(RecognizedSong.created_at >= day_ago)
        )
        videos_day = await self.session.execute(
            select(func.count(SavedVideo.id)).where(SavedVideo.created_at >= day_ago)
        )

        return {
            "users_last_24h": int(users_day.scalar_one()),
            "users_last_7d": int(users_week.scalar_one()),
            "searches_last_24h": int(searches_day.scalar_one()),
            "searches_last_7d": int(searches_week.scalar_one()),
            "recognized_last_24h": int(recognized_day.scalar_one()),
            "videos_last_24h": int(videos_day.scalar_one()),
        }
