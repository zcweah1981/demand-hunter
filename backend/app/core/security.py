from __future__ import annotations
import hmac, secrets
from fastapi import Header, HTTPException
from .config import config

AUTH_TOKEN = config.auth_token or secrets.token_urlsafe(32)
AUTH_PASSWORD = config.auth_password

def require_auth(authorization: str | None = Header(default=None)):
    if not AUTH_PASSWORD:
        return True
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='unauthorized')
    token = authorization.split(' ', 1)[1]
    if not hmac.compare_digest(token, AUTH_TOKEN):
        raise HTTPException(status_code=401, detail='unauthorized')
    return True
