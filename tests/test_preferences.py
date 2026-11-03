from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import PASSWORD
from tests.helpers import API


def get(client: TestClient) -> dict:
    response = client.get(f"{API}/preferences")
    assert response.status_code == 200, response.text
    return response.json()


def set_view(client: TestClient, value: object):
    return client.patch(f"{API}/preferences", json={"default_view": value})


def test_the_default_view_starts_as_month(client: TestClient) -> None:
    assert get(client) == {"default_view": "month", "theme": None}


@pytest.mark.parametrize("view", ["day", "week", "month"])
def test_choosing_a_default_view(client: TestClient, view: str) -> None:
    response = set_view(client, view)

    assert response.status_code == 200
    assert response.json() == {"default_view": view, "theme": None}
    assert get(client) == {"default_view": view, "theme": None}


def test_the_choice_is_saved_on_the_server(
    client: TestClient, sign_in: Callable[..., TestClient], engine: Engine
) -> None:
    set_view(client, "week")

    other_device = sign_in("alice")  # a new session of the same user
    assert get(other_device)["default_view"] == "week"
    with Session(engine) as session:
        assert session.scalar(select(User.default_view).where(User.username == "alice")) == "week"


def test_each_user_has_their_own_default_view(
    client: TestClient, sign_in: Callable[..., TestClient]
) -> None:
    bob = sign_in("bob")

    set_view(client, "day")
    set_view(bob, "week")

    assert get(client)["default_view"] == "day"
    assert get(bob)["default_view"] == "week"


@pytest.mark.parametrize("value", ["year", "all", "Month", "", "weekly", 1, ["day"], {"a": 1}])
def test_only_day_week_and_month_are_accepted(client: TestClient, value: object) -> None:
    set_view(client, "day")

    response = set_view(client, value)

    assert response.status_code == 422
    assert "default_view" in response.json()["detail"]
    assert get(client)["default_view"] == "day", "a rejected change must not change anything"


def test_an_empty_update_changes_nothing(client: TestClient) -> None:
    set_view(client, "week")

    response = client.patch(f"{API}/preferences", json={})

    assert response.status_code == 200
    assert response.json()["default_view"] == "week"


def test_null_does_not_reset_the_view(client: TestClient) -> None:
    set_view(client, "week")

    assert set_view(client, None).json()["default_view"] == "week"


def test_preferences_need_a_signed_in_user(client_factory) -> None:
    anonymous = client_factory()

    assert anonymous.get(f"{API}/preferences").status_code == 401
    assert anonymous.patch(f"{API}/preferences", json={"default_view": "day"}).status_code == 401


def test_the_view_survives_signing_out_and_in_again(client: TestClient) -> None:
    set_view(client, "day")
    client.post(f"{API}/auth/logout")

    client.post(f"{API}/auth/login", json={"username": "alice", "password": PASSWORD})

    assert get(client)["default_view"] == "day"


def test_the_view_survives_a_password_change(client: TestClient) -> None:
    set_view(client, "week")

    client.post(
        f"{API}/auth/password",
        json={"current_password": PASSWORD, "new_password": "a different password"},
    )

    assert get(client)["default_view"] == "week"


def test_new_accounts_start_with_month(client_factory) -> None:
    fresh = client_factory()
    fresh.post(f"{API}/auth/register", json={"username": "carol", "password": PASSWORD})

    assert get(fresh) == {"default_view": "month", "theme": None}


def test_the_view_is_not_part_of_the_data_export(client: TestClient) -> None:
    set_view(client, "day")
    client.post(f"{API}/tracks", json={"name": "T"})

    exported = client.get(f"{API}/export").json()

    assert "default_view" not in str(exported) and "theme" not in str(exported)


# --- theme ---

THEMES = ["auto", "graphite", "midnight", "forest", "ember", "paper", "sand"]


def set_theme(client: TestClient, value: object):
    return client.patch(f"{API}/preferences", json={"theme": value})


def test_no_theme_is_chosen_at_first(client: TestClient) -> None:
    assert get(client)["theme"] is None


@pytest.mark.parametrize("theme", THEMES)
def test_choosing_a_theme(client: TestClient, theme: str) -> None:
    response = set_theme(client, theme)

    assert response.status_code == 200
    assert response.json()["theme"] == theme
    assert get(client)["theme"] == theme


@pytest.mark.parametrize("value", ["purple", "Graphite", "", "dark", 3, ["sand"], {"a": 1}])
def test_only_known_themes_are_accepted(client: TestClient, value: object) -> None:
    set_theme(client, "sand")

    response = set_theme(client, value)

    assert response.status_code == 422
    assert "theme" in response.json()["detail"]
    assert get(client)["theme"] == "sand"


def test_the_theme_follows_the_account_to_other_devices(
    client: TestClient, sign_in: Callable[..., TestClient], engine: Engine
) -> None:
    set_theme(client, "midnight")

    other_device = sign_in("alice")

    assert get(other_device)["theme"] == "midnight"
    with Session(engine) as session:
        assert session.scalar(select(User.theme).where(User.username == "alice")) == "midnight"


def test_each_user_has_their_own_theme(
    client: TestClient, sign_in: Callable[..., TestClient]
) -> None:
    bob = sign_in("bob")

    set_theme(client, "forest")
    set_theme(bob, "paper")

    assert get(client)["theme"] == "forest"
    assert get(bob)["theme"] == "paper"


def test_the_theme_and_the_view_are_independent(client: TestClient) -> None:
    set_theme(client, "ember")
    set_view(client, "day")
    assert get(client) == {"default_view": "day", "theme": "ember"}

    set_theme(client, "sand")
    assert get(client) == {"default_view": "day", "theme": "sand"}

    set_view(client, "week")
    assert get(client) == {"default_view": "week", "theme": "sand"}


def test_both_can_be_changed_in_one_request(client: TestClient) -> None:
    response = client.patch(f"{API}/preferences", json={"default_view": "week", "theme": "forest"})

    assert response.json() == {"default_view": "week", "theme": "forest"}


def test_null_does_not_clear_the_theme(client: TestClient) -> None:
    set_theme(client, "sand")

    assert set_theme(client, None).json()["theme"] == "sand"
    assert client.patch(f"{API}/preferences", json={}).json()["theme"] == "sand"


def test_a_retired_theme_reads_back_as_automatic(client: TestClient, engine: Engine) -> None:
    with Session(engine) as session:
        user = session.scalar(select(User).where(User.username == "alice"))
        user.theme = "a-theme-that-was-removed"
        session.commit()

    response = client.get(f"{API}/preferences")

    assert response.status_code == 200
    assert response.json()["theme"] == "auto"


def test_the_theme_survives_signing_out_and_a_password_change(client: TestClient) -> None:
    set_theme(client, "paper")
    client.post(f"{API}/auth/logout")
    client.post(f"{API}/auth/login", json={"username": "alice", "password": PASSWORD})
    assert get(client)["theme"] == "paper"

    client.post(
        f"{API}/auth/password",
        json={"current_password": PASSWORD, "new_password": "a different password"},
    )

    assert get(client)["theme"] == "paper"


def test_the_server_knows_exactly_the_themes_the_app_offers() -> None:
    import re
    from pathlib import Path

    from app.schemas import THEME_IDS

    static = Path(__file__).resolve().parent.parent / "app" / "static"
    in_script = re.findall(r'\{ id: "(\w+)"', (static / "js" / "theme.js").read_text())
    in_css = re.findall(r'\[data-theme="(\w+)"\] \{', (static / "css" / "app.css").read_text())

    assert list(THEME_IDS) == in_script == THEMES
    assert sorted(set(in_css)) == sorted(set(THEME_IDS) - {"auto"})
