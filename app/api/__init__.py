from fastapi import APIRouter

from app.api.routes import router as api_router

api = APIRouter(prefix="/api")
api.include_router(api_router)
