from __future__ import annotations
from fastapi import APIRouter
from app.api.v1.endpoints import auth, discovery, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(discovery.router)
