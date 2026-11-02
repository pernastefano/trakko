import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import auth
from tests.conftest import ClientFactory
from tests.helpers import API

PASSWORD = "correct horse"
SECRET = "test-secret-key"


@pytest.fixture
def secured(client_factory: ClientFactory) -> TestClient:
    return client_factory(password=PASSWORD, secret_key=SECRET)


def login(client: TestClient, password: str = PASSWORD):
    return client.post(f"{API}/auth/login", json={"password": password})


def test_without_a_password_everything_is_open(client: TestClient) -> None:
    assert client.get(f"{API}/tracks").status_code == 200
    assert client.get(f"{API}/auth/status").json() == {
        "auth_required": False,
        "authenticated": True,
    }


def test_protected_routes_require_a_session(secured: TestClient) -> None:
    for path in ("/tracks", "/entries", "/export", "/stats?track_id=1", "/tracks/1/event-types"):
        response = secured.get(f"{API}{path}")
        assert response.status_code == 401, path
        assert response.json() == {"detail": "Authentication required"}
    assert secured.post(f"{API}/import", json={}).status_code == 401


def test_health_and_status_stay_public(secured: TestClient) -> None:
    assert secured.get("/health").status_code == 200
    assert secured.get(f"{API}/auth/status").json() == {
        "auth_required": True,
        "authenticated": False,
    }


def test_wrong_password(secured: TestClient) -> None:
    response = login(secured, "nope")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid password"}
    assert auth.COOKIE_NAME not in response.cookies
    assert secured.get(f"{API}/tracks").status_code == 401


def test_login_sets_an_http_only_cookie_that_unlocks_the_api(secured: TestClient) -> None:
    response = login(secured)

    assert response.status_code == 200
    assert response.json() == {"auth_required": True, "authenticated": True}
    set_cookie = response.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert secured.get(f"{API}/tracks").status_code == 200
    assert secured.get(f"{API}/auth/status").json()["authenticated"] is True


def test_logout_locks_the_api_again(secured: TestClient) -> None:
    login(secured)

    assert secured.post(f"{API}/auth/logout").status_code == 204
    assert secured.get(f"{API}/tracks").status_code == 401


def test_forged_and_tampered_cookies_are_rejected(secured: TestClient) -> None:
    valid = auth.create_token(SECRET)
    expires, _, signature = valid.partition(".")
    for token in ("garbage", "", f"{expires}.", f"9999999999.{signature}", valid + "0"):
        secured.cookies.set(auth.COOKIE_NAME, token)
        assert secured.get(f"{API}/tracks").status_code == 401, token


def test_cookie_signed_with_another_key_is_rejected(secured: TestClient) -> None:
    secured.cookies.set(auth.COOKIE_NAME, auth.create_token("some-other-key"))

    assert secured.get(f"{API}/tracks").status_code == 401


def test_token_expiry() -> None:
    token = auth.create_token(SECRET, now=1_000)

    assert auth.verify_token(SECRET, token, now=1_000 + auth.SESSION_SECONDS - 1)
    assert not auth.verify_token(SECRET, token, now=1_000 + auth.SESSION_SECONDS)


def test_secret_key_is_required_when_a_password_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import main

    monkeypatch.setattr(
        main, "get_settings", lambda: Settings(db_path="x", password="pw", secret_key=None)
    )

    with pytest.raises(RuntimeError, match="TRAKKO_SECRET_KEY"):
        create_app()
