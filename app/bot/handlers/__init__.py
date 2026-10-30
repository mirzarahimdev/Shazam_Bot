from aiogram import Router

from app.bot.handlers import admin, search, start


def get_routers() -> list[Router]:
    return [
        start.router,
        search.router,
        admin.router,
    ]
