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
    use_four_find: bool | None = None
    seeds: list[str] | None = None


class AuthLoginIn(BaseModel):
    password: str

class AuthLoginOut(BaseModel):
    token: str

class AutoTickIn(BaseModel):
    force: bool = False

class DiscoverySeedIn(BaseModel):
    seed: str
    depth: int | None = 2
    import_limit: int | None = 12

class DiscoveryDomainIn(BaseModel):
    domain: str

class AuthPasswordChangeIn(BaseModel):
    current_password: str
    new_password: str

class SettingKeyAppendIn(BaseModel):
    key: str
    value: str

class SettingKeyClearIn(BaseModel):
    key: str

class SearxngEndpointIn(BaseModel):
    url: str
    api_token: str = ""

class SearxngEndpointsIn(BaseModel):
    endpoints: list[SearxngEndpointIn]

class LLMFallbackAppendIn(BaseModel):
    provider: str
    model: str
    api_key: str = ""

class LLMFallbackRemoveIn(BaseModel):
    index: int

class SettingKeyRemoveIn(BaseModel):
    key: str
    index: int
