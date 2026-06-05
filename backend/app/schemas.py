from __future__ import annotations
from pydantic import BaseModel
from typing import Any

class SettingIn(BaseModel):
    key: str
    value: str = ""
    secret: bool = False

class RootIn(BaseModel):
    term: str
    category: str = "tool"
    enabled: bool = True
    weight: float = 1.0
    notes: str = ""

class KeywordIn(BaseModel):
    query: str
    source: str = "manual"
    root_terms: list[str] = []

class FeedbackIn(BaseModel):
    label: str
    note: str = ""

class DailyRunIn(BaseModel):
    limit: int = 12
    roots: list[str] | None = None


class AuthLoginIn(BaseModel):
    password: str

class AuthLoginOut(BaseModel):
    token: str

class AutoTickIn(BaseModel):
    force: bool = False
