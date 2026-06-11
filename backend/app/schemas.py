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

class RepairActionIn(BaseModel):
    action: str
    source: str | None = None
    value: str | None = None

class RepairRollbackIn(BaseModel):
    repair_id: int

class RepairExperimentIn(BaseModel):
    action: str
    source: str | None = None
    value: str | None = None
    force_run: bool = True

class RepairExperimentAbandonIn(BaseModel):
    experiment_id: int
    rollback: bool = False

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
    use_builtin_engines: bool = True
    engines: str = ""

class SearxngEndpointsIn(BaseModel):
    endpoints: list[SearxngEndpointIn]

class LLMFallbackAppendIn(BaseModel):
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""

class LLMFallbackIn(BaseModel):
    base_url: str
    model: str = ""
    api_key: str = ""

class LLMFallbacksIn(BaseModel):
    fallbacks: list[LLMFallbackIn]

class LLMFallbackRemoveIn(BaseModel):
    index: int

class LLMModelsIn(BaseModel):
    base_url: str
    api_key: str = ""
    fallback_index: int | None = None

class SettingKeyRemoveIn(BaseModel):
    key: str
    index: int

class SettingKeyRevealIn(BaseModel):
    key: str
    index: int | None = None

class ApiKeyEntryIn(BaseModel):
    type_id: str
    values: dict[str, Any]

class ApiKeyEntryUpdateIn(BaseModel):
    type_id: str
    index: int
    values: dict[str, Any]

class ApiKeyEntryRemoveIn(BaseModel):
    type_id: str
    index: int

class CollectorSitemapIn(BaseModel):
    domains: list[str]
    max_urls_per_domain: int = 80
    only_new: bool = True

class CollectorSuggestIn(BaseModel):
    seeds: list[str]

class CandidateImportIn(BaseModel):
    limit: int = 30

class CollectorAdvancedSearchIn(BaseModel):
    roots: list[str]
    domains: list[str] = []
    days: int = 30
    limit_per_query: int = 8

class CollectorSourceRadarIn(BaseModel):
    seeds: list[str]
    limit_per_seed: int = 10


class CandidateEntryIn(BaseModel):
    entry_type: str
    name: str
    source: str = ""
    source_role: str = ""
    source_url: str = ""
    raw_context: dict[str, Any] = {}
    priority: float = 0.0
