from __future__ import annotations
import hmac, json, secrets
from pathlib import Path
from fastapi import Header, HTTPException
from .config import config

AUTH_TOKEN = config.auth_token or secrets.token_urlsafe(32)
AUTH_PASSWORD = config.auth_password
AUTH_FILE = Path(__file__).resolve().parents[2] / 'data' / 'auth.json'


def get_auth_password() -> str:
    try:
        if AUTH_FILE.exists():
            data = json.loads(AUTH_FILE.read_text())
            if data.get('password'):
                return str(data['password'])
    except Exception:
        pass
    return AUTH_PASSWORD


def set_auth_password(password: str):
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(json.dumps({'password': password}, ensure_ascii=False))


def require_auth(authorization: str | None = Header(default=None)):
    password = get_auth_password()
    if not password:
        return True
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='unauthorized')
    token = authorization.split(' ', 1)[1]
    if not hmac.compare_digest(token, AUTH_TOKEN):
        raise HTTPException(status_code=401, detail='unauthorized')
    return True
