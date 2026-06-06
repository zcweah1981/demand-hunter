from __future__ import annotations
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine, configure_sqlite
from app import services
from app.api.v1.api import api_router
from app.core.config import config
from app.main_runtime import auto_loop

configure_sqlite()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Demand Hunter API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)

@app.on_event("startup")
def startup():
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        services.init_defaults(db)
    finally:
        db.close()
    if config.auto_worker_enabled:
        threading.Thread(target=auto_loop, daemon=True).start()
