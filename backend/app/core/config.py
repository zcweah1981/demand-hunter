from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    auth_token: str = os.environ.get('DEMAND_HUNTER_AUTH_TOKEN', '')
    auth_password: str = os.environ.get('DEMAND_HUNTER_PASSWORD', '')
    auto_worker: str = os.environ.get('DEMAND_HUNTER_AUTO_WORKER', 'true')
    cors_origins: str = os.environ.get('DEMAND_HUNTER_CORS_ORIGINS', '*')

    @property
    def auto_worker_enabled(self) -> bool:
        return self.auto_worker.lower() in {'1','true','yes','on'}

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins or self.cors_origins == '*':
            return ['*']
        return [x.strip() for x in self.cors_origins.split(',') if x.strip()]

config = AppConfig()
