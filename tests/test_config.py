import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def clear_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("TRAKKO_DB_PATH", "TRAKKO_SECRET_KEY", "TRAKKO_ALLOW_REGISTRATION"):
        monkeypatch.delenv(name, raising=False)


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_environment(monkeypatch)

    settings = get_settings()

    assert settings.db_path == "data/trakko.db"
    assert settings.allow_registration is True
    assert settings.secret_key_is_random is True
    assert len(settings.secret_key) >= 32


def test_random_key_is_stable_within_a_process(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_environment(monkeypatch)

    assert get_settings().secret_key == get_settings().secret_key


def test_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_environment(monkeypatch)
    monkeypatch.setenv("TRAKKO_DB_PATH", "/tmp/x.db")
    monkeypatch.setenv("TRAKKO_SECRET_KEY", "key")
    monkeypatch.setenv("TRAKKO_ALLOW_REGISTRATION", "false")

    settings = get_settings()

    assert settings.db_path == "/tmp/x.db"
    assert (settings.secret_key, settings.secret_key_is_random) == ("key", False)
    assert settings.allow_registration is False


@pytest.mark.parametrize("value", ["false", "FALSE", " no ", "0", "off"])
def test_registration_can_be_switched_off(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    clear_environment(monkeypatch)
    monkeypatch.setenv("TRAKKO_ALLOW_REGISTRATION", value)

    assert get_settings().allow_registration is False


@pytest.mark.parametrize("value", ["true", "1", "yes", "", "anything"])
def test_registration_stays_open_otherwise(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    clear_environment(monkeypatch)
    monkeypatch.setenv("TRAKKO_ALLOW_REGISTRATION", value)

    assert get_settings().allow_registration is True
