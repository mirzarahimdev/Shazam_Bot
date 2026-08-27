from aiogram import Router

from app.bot.handlers import admin, favorites, profile, recognize, search, settings, start, video


def get_routers() -> list[Router]:
    return [
        start.router,
        search.router,
        recognize.router,
        video.router,
        favorites.router,
        profile.router,
        settings.router,
        admin.router,
    ]
