from __future__ import annotations
from fastapi import APIRouter
from app.api.v1.endpoints import auth, auto, autopilot, cards, collectors, discovery, entries, evidence, health, keywords, progress, reports, roots, runs, settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(autopilot.router)
api_router.include_router(settings.router)
api_router.include_router(collectors.router)
api_router.include_router(entries.router)
api_router.include_router(evidence.router)
api_router.include_router(discovery.router)
api_router.include_router(roots.router)
api_router.include_router(keywords.router)
api_router.include_router(cards.router)
api_router.include_router(progress.router)
api_router.include_router(runs.router)
api_router.include_router(auto.router)
api_router.include_router(reports.router)
