import os
import secrets
from dataclasses import dataclass
from functools import lru_cache

FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class Settings:
    db_path: str
    secret_key: str
    secret_key_is_random: bool
    allow_registration: bool


@lru_cache
def get_settings() -> Settings:
    configured_key = os.environ.get("TRAKKO_SECRET_KEY")
    allow = os.environ.get("TRAKKO_ALLOW_REGISTRATION", "true").strip().lower()
    return Settings(
        db_path=os.environ.get("TRAKKO_DB_PATH") or "data/trakko.db",
        # Without a configured key sessions only live until the process restarts.
        secret_key=configured_key or secrets.token_urlsafe(48),
        secret_key_is_random=not configured_key,
        allow_registration=allow not in FALSE_VALUES,
    )
