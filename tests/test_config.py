import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("TRAKKO_DB_PATH", "TRAKKO_PASSWORD", "TRAKKO_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)

    settings = get_settings()

    assert settings.db_path == "data/trakko.db"
    assert settings.password is None
    assert settings.secret_key is None


def test_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAKKO_DB_PATH", "/tmp/x.db")
    monkeypatch.setenv("TRAKKO_PASSWORD", "pw")
    monkeypatch.setenv("TRAKKO_SECRET_KEY", "key")

    settings = get_settings()

    assert settings.db_path == "/tmp/x.db"
    assert settings.password == "pw"
    assert settings.secret_key == "key"
