from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models import User
from app.services import auth
from tests.conftest import PASSWORD
from tests.helpers import API

NEW_PASSWORD = "a brand new password"


def change(client: TestClient, current: str = PASSWORD, new: str = NEW_PASSWORD):
    return client.post(
        f"{API}/auth/password", json={"current_password": current, "new_password": new}
    )


def login(client: TestClient, username: str, password: str):
    return client.post(f"{API}/auth/login", json={"username": username, "password": password})


def test_changing_the_password(client: TestClient, client_factory) -> None:
    response = change(client)

    assert response.status_code == 204
    fresh = client_factory()
    assert login(fresh, "alice", PASSWORD).status_code == 401, "the old password is gone"
    assert login(fresh, "alice", NEW_PASSWORD).status_code == 200


def test_the_device_that_changed_it_stays_signed_in(client: TestClient) -> None:
    response = change(client)

    assert auth.COOKIE_NAME in response.headers["set-cookie"]
    assert client.get(f"{API}/tracks").status_code == 200
    assert client.get(f"{API}/auth/status").json()["username"] == "alice"


def test_every_other_session_of_that_user_ends(
    client: TestClient, sign_in: Callable[..., TestClient]
) -> None:
    other_device = sign_in("alice")
    assert other_device.get(f"{API}/tracks").status_code == 200

    change(client)

    assert other_device.get(f"{API}/tracks").status_code == 401
    assert other_device.get(f"{API}/auth/status").json()["authenticated"] is False


def test_other_users_are_not_affected(
    client: TestClient, sign_in: Callable[..., TestClient]
) -> None:
    bob = sign_in("bob")

    change(client)

    assert bob.get(f"{API}/tracks").status_code == 200


def test_the_new_hash_is_salted_and_the_old_one_is_replaced(
    client: TestClient, engine: Engine
) -> None:
    with Session(engine) as session:
        before = session.scalar(select(User.password_hash).where(User.username == "alice"))

    change(client)

    with Session(engine) as session:
        after = session.scalar(select(User.password_hash).where(User.username == "alice"))
    assert after != before
    assert NEW_PASSWORD not in after and after.startswith("scrypt$")


def test_the_current_password_must_be_right(client: TestClient, client_factory) -> None:
    response = change(client, current="not my password")

    assert response.status_code == 403
    assert response.json() == {"detail": "The current password is not correct"}
    assert login(client_factory(), "alice", PASSWORD).status_code == 200, "nothing changed"


@pytest.mark.parametrize("new", ["short", "1234567", "x" * 129, ""])
def test_the_new_password_must_be_acceptable(client: TestClient, new: str) -> None:
    response = change(client, new=new)

    assert response.status_code == 422
    assert "new_password" in response.json()["detail"]


def test_the_new_password_must_differ(client: TestClient) -> None:
    response = change(client, new=PASSWORD)

    assert response.status_code == 422
    assert "different" in response.json()["detail"]


def test_a_missing_current_password_is_rejected(client: TestClient) -> None:
    response = client.post(f"{API}/auth/password", json={"new_password": NEW_PASSWORD})

    assert response.status_code == 422
    assert "current_password" in response.json()["detail"]


def test_you_must_be_signed_in(client_factory) -> None:
    anonymous = client_factory()

    response = change(anonymous)

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_password_change_keeps_the_data(client: TestClient) -> None:
    client.post(f"{API}/tracks", json={"name": "Mine"})

    change(client)

    assert [t["name"] for t in client.get(f"{API}/tracks").json()] == ["Mine"]
