from __future__ import annotations
import hmac
from fastapi import APIRouter, Depends, HTTPException
from app import schemas
from app.core.security import AUTH_PASSWORD, AUTH_TOKEN, require_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(payload: schemas.AuthLoginIn):
    if not AUTH_PASSWORD:
        return {"token": AUTH_TOKEN, "auth_enabled": False}
    if not hmac.compare_digest(payload.password, AUTH_PASSWORD):
        raise HTTPException(status_code=401, detail="invalid password")
    return {"token": AUTH_TOKEN, "auth_enabled": True}

@router.get("/me")
def me(_: bool = Depends(require_auth)):
    return {"ok": True, "auth_enabled": bool(AUTH_PASSWORD)}
