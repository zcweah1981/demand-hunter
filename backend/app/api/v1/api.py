from __future__ import annotations
from fastapi import APIRouter
from app.api.v1.endpoints import auth, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(settings.router)
