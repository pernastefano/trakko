import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.models import Track, User
from app.services import auth, users
from tests.conftest import PASSWORD, ClientFactory
from tests.helpers import API

KEY = "test-secret-key"


def register(client: TestClient, username: str = "alice", password: str = PASSWORD):
    return client.post(f"{API}/auth/register", json={"username": username, "password": password})


def login(client: TestClient, username: str = "alice", password: str = PASSWORD):
    return client.post(f"{API}/auth/login", json={"username": username, "password": password})


@pytest.fixture
def anonymous(client_factory: ClientFactory) -> TestClient:
    return client_factory()


# --- everything but the auth endpoints needs a user ---


def test_protected_routes_require_a_session(anonymous: TestClient) -> None:
    for path in ("/tracks", "/entries", "/export", "/stats?track_id=1", "/tracks/1/event-types"):
        response = anonymous.get(f"{API}{path}")
        assert response.status_code == 401, path
        assert response.json() == {"detail": "Authentication required"}
    assert anonymous.post(f"{API}/import", json={}).status_code == 401
    assert anonymous.post(f"{API}/tracks", json={"name": "x"}).status_code == 401


def test_health_the_page_and_status_stay_public(anonymous: TestClient) -> None:
    assert anonymous.get("/health").status_code == 200
    assert anonymous.get("/").status_code == 200
    assert anonymous.get(f"{API}/auth/status").json() == {
        "authenticated": False,
        "username": None,
        "registration_open": True,
    }


# --- registration ---


def test_registering_signs_you_in_and_creates_a_default_track(anonymous: TestClient) -> None:
    response = register(anonymous, "Alice")

    assert response.status_code == 201
    assert response.json() == {
        "authenticated": True,
        "username": "alice",
        "registration_open": True,
    }
    tracks = anonymous.get(f"{API}/tracks").json()
    assert [(t["name"], t["is_default"]) for t in tracks] == [("My Track", True)]
    assert anonymous.get(f"{API}/auth/status").json()["username"] == "alice"


def test_session_cookie_is_http_only_and_lax(anonymous: TestClient) -> None:
    header = register(anonymous).headers["set-cookie"].lower()

    assert header.startswith(f"{auth.COOKIE_NAME}=")
    assert "httponly" in header and "samesite=lax" in header


def test_usernames_are_case_insensitive_and_unique(anonymous: TestClient, engine: Engine) -> None:
    register(anonymous, "alice")

    response = register(anonymous, "ALICE")

    assert response.status_code == 409
    assert response.json() == {"detail": "That username is already taken"}
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize(
    "username",
    ["ab", "a" * 33, "has space", "-leading", "emoji🙂", "semi;colon", "slash/name", ""],
)
def test_invalid_usernames_are_rejected(anonymous: TestClient, username: str) -> None:
    response = register(anonymous, username)

    assert response.status_code == 422
    assert "username" in response.json()["detail"]


@pytest.mark.parametrize("username", ["abc", "a.b-c_d", "user123", "a" * 32, "  Padded  "])
def test_valid_usernames_are_accepted(anonymous: TestClient, username: str) -> None:
    assert register(anonymous, username).status_code == 201


@pytest.mark.parametrize("password", ["short", "1234567", "x" * 129, ""])
def test_invalid_passwords_are_rejected(anonymous: TestClient, password: str) -> None:
    response = register(anonymous, "alice", password)

    assert response.status_code == 422
    assert "password" in response.json()["detail"]


def test_registration_can_be_closed(client_factory: ClientFactory, engine: Engine) -> None:
    open_client = client_factory()
    register(open_client, "first")
    closed = client_factory(allow_registration=False)

    response = register(closed, "second")

    assert response.status_code == 403
    assert response.json() == {"detail": "Registration is closed"}
    assert closed.get(f"{API}/auth/status").json()["registration_open"] is False
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1


def test_registration_stays_possible_while_there_is_no_account(
    client_factory: ClientFactory,
) -> None:
    closed = client_factory(allow_registration=False)

    assert closed.get(f"{API}/auth/status").json()["registration_open"] is True
    assert register(closed, "first").status_code == 201
    assert closed.get(f"{API}/auth/status").json()["registration_open"] is False


# --- sign in and out ---


def test_login_with_the_right_credentials(anonymous: TestClient, client_factory) -> None:
    register(anonymous, "alice")
    other_device = client_factory()

    response = login(other_device, "Alice")  # case does not matter

    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert other_device.get(f"{API}/tracks").status_code == 200


def test_login_failures_do_not_say_which_part_was_wrong(
    anonymous: TestClient, client_factory
) -> None:
    register(anonymous, "alice")
    fresh = client_factory()

    wrong_password = login(fresh, "alice", "not the password")
    unknown_user = login(fresh, "nobody", PASSWORD)

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert (
        wrong_password.json() == unknown_user.json() == {"detail": "Invalid username or password"}
    )
    assert auth.COOKIE_NAME not in wrong_password.cookies
    assert fresh.get(f"{API}/tracks").status_code == 401


def test_logout_locks_the_api_again(client: TestClient) -> None:
    assert client.get(f"{API}/tracks").status_code == 200

    assert client.post(f"{API}/auth/logout").status_code == 204

    assert client.get(f"{API}/tracks").status_code == 401
    assert client.get(f"{API}/auth/status").json()["authenticated"] is False


def test_login_after_logout_works(client: TestClient) -> None:
    client.post(f"{API}/auth/logout")

    assert login(client).status_code == 200
    assert client.get(f"{API}/tracks").status_code == 200


# --- tokens and cookies ---


def test_forged_and_tampered_cookies_are_rejected(client: TestClient) -> None:
    token = auth.create_token(KEY, 1, "some-hash")
    user_id, expires, token_fingerprint, signature = token.split(".")
    forged = [
        "garbage",
        "",
        "1.",
        "1.2.3",
        f"1.{expires}.{token_fingerprint}.",
        f"2.{expires}.{token_fingerprint}.{signature}",  # someone else's id, same signature
        f"{user_id}.9999999999.{token_fingerprint}.{signature}",  # later expiry, same signature
        f"{user_id}.{expires}.{'0' * 16}.{signature}",  # other fingerprint, same signature
        token + "0",
    ]
    for value in forged:
        client.cookies.set(auth.COOKIE_NAME, value)
        assert client.get(f"{API}/tracks").status_code == 401, value


def test_cookie_signed_with_another_key_is_rejected(client: TestClient) -> None:
    client.cookies.set(auth.COOKIE_NAME, auth.create_token("some-other-key", 1, "some-hash"))

    assert client.get(f"{API}/tracks").status_code == 401


def test_a_genuine_token_for_an_old_password_is_rejected(
    client: TestClient, engine: Engine
) -> None:
    with Session(engine) as session:
        user = session.scalar(select(User))
        stale = auth.create_token(KEY, user.id, "the-hash-before-the-password-changed")
    client.cookies.set(auth.COOKIE_NAME, stale)

    assert client.get(f"{API}/tracks").status_code == 401


def test_cookie_of_a_deleted_user_is_rejected(client: TestClient, engine: Engine) -> None:
    with Session(engine) as session:
        session.delete(session.scalar(select(User)))
        session.commit()

    assert client.get(f"{API}/tracks").status_code == 401


def test_token_carries_the_user_and_the_password_fingerprint_and_expires() -> None:
    token = auth.create_token(KEY, 42, "hash-a", now=1_000)
    expected = (42, auth.fingerprint(KEY, "hash-a"))

    assert auth.parse_token(KEY, token, now=1_000 + auth.SESSION_SECONDS - 1) == expected
    assert auth.parse_token(KEY, token, now=1_000 + auth.SESSION_SECONDS) is None
    assert auth.parse_token("another key", token, now=1_000) is None


def test_fingerprint_changes_with_the_password_and_does_not_leak_it() -> None:
    first = auth.fingerprint(KEY, "hash-a")

    assert first != auth.fingerprint(KEY, "hash-b")
    assert first != auth.fingerprint("another key", "hash-a")
    assert "hash-a" not in first and len(first) == auth.FINGERPRINT_LENGTH


# --- password hashing ---


def test_passwords_are_hashed_with_a_salt(engine: Engine) -> None:
    with Session(engine) as session:
        first = users.create_user(session, "alice", PASSWORD, with_default_track=False)
        second = users.create_user(session, "bob", PASSWORD, with_default_track=False)
        hashes = (first.password_hash, second.password_hash)

    assert all(h.startswith("scrypt$") and PASSWORD not in h for h in hashes)
    assert hashes[0] != hashes[1], "equal passwords must not give equal hashes"
    assert all(users.verify_password(PASSWORD, h) for h in hashes)
    assert not users.verify_password("wrong password", hashes[0])


@pytest.mark.parametrize("stored", ["", "plain", "scrypt$a$b$c$d$e", "md5$1$2$3$4$5", "scrypt$1$2"])
def test_malformed_stored_hashes_never_verify(stored: str) -> None:
    assert users.verify_password(PASSWORD, stored) is False


def test_hash_parameters_are_stored_with_the_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    stored = users.hash_password(PASSWORD)
    monkeypatch.setattr(users, "SCRYPT_N", 2**5)  # changing the cost later must not break it

    assert stored.split("$")[1] == str(2**4)
    assert users.verify_password(PASSWORD, stored)


def test_production_cost_is_not_the_test_cost() -> None:
    import importlib

    fresh = importlib.reload(users)  # the autouse fixture only patched the old value

    assert fresh.SCRYPT_N >= 2**14


def test_new_accounts_have_one_default_track_and_nothing_else(
    anonymous: TestClient, engine: Engine
) -> None:
    register(anonymous, "alice")
    register(anonymous, "alice2")

    with Session(engine) as session:
        names = session.scalars(select(Track.name)).all()
    assert names == ["My Track", "My Track"]
