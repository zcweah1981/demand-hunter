from __future__ import annotations
import hmac
from fastapi import APIRouter, Depends, HTTPException
from app import schemas
from app.core.security import AUTH_TOKEN, get_auth_password, require_auth, set_auth_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(payload: schemas.AuthLoginIn):
    password = get_auth_password()
    if not password:
        return {"token": AUTH_TOKEN, "auth_enabled": False}
    if not hmac.compare_digest(payload.password, password):
        raise HTTPException(status_code=401, detail="invalid password")
    return {"token": AUTH_TOKEN, "auth_enabled": True}

@router.get("/me")
def me(_: bool = Depends(require_auth)):
    return {"ok": True, "auth_enabled": bool(get_auth_password())}

@router.post("/password")
def change_password(payload: schemas.AuthPasswordChangeIn, _: bool = Depends(require_auth)):
    current = get_auth_password()
    if current and not hmac.compare_digest(payload.current_password, current):
        raise HTTPException(status_code=401, detail="invalid current password")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="password too short")
    set_auth_password(payload.new_password)
    return {"ok": True}
