import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    db_path: str
    password: str | None
    secret_key: str | None


@lru_cache
def get_settings() -> Settings:
    return Settings(
        db_path=os.environ.get("TRAKKO_DB_PATH") or "data/trakko.db",
        password=os.environ.get("TRAKKO_PASSWORD") or None,
        secret_key=os.environ.get("TRAKKO_SECRET_KEY") or None,
    )
