"""Two people share one installation: nobody sees or touches anybody else's data."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from tests.helpers import API, create_entry, create_event_type, create_track


@pytest.fixture
def alice(sign_in: Callable[..., TestClient]) -> TestClient:
    return sign_in("alice")


@pytest.fixture
def bob(sign_in: Callable[..., TestClient]) -> TestClient:
    return sign_in("bob")


@pytest.fixture
def alices(alice: TestClient) -> dict:
    """Alice's Track with one Event Type and one entry."""
    track = create_track(alice, "Alice's track")
    event_type = create_event_type(alice, track["id"], "Running")
    entry = create_entry(alice, event_type["id"], "2026-11-02", "secret note")
    return {"track": track, "event_type": event_type, "entry": entry}


def test_lists_only_show_your_own_data(alice: TestClient, bob: TestClient, alices: dict) -> None:
    mine = create_track(bob, "Bob's track")
    bob_type = create_event_type(bob, mine["id"], "Reading")
    create_entry(bob, bob_type["id"], "2026-11-03")

    assert [t["name"] for t in alice.get(f"{API}/tracks").json()] == ["Alice's track"]
    assert [t["name"] for t in bob.get(f"{API}/tracks").json()] == ["Bob's track"]
    assert [e["date"] for e in alice.get(f"{API}/entries").json()] == ["2026-11-02"]
    assert [e["date"] for e in bob.get(f"{API}/entries").json()] == ["2026-11-03"]


def test_each_user_has_their_own_default_track(alice: TestClient, bob: TestClient) -> None:
    first_a = create_track(alice, "A1")
    second_a = create_track(alice, "A2")
    first_b = create_track(bob, "B1")

    assert (first_a["is_default"], second_a["is_default"], first_b["is_default"]) == (
        True,
        False,
        True,
    )


def test_making_a_track_default_does_not_affect_other_users(
    alice: TestClient, bob: TestClient
) -> None:
    create_track(alice, "A1")
    second_a = create_track(alice, "A2")
    first_b = create_track(bob, "B1")

    alice.patch(f"{API}/tracks/{second_a['id']}", json={"is_default": True})

    assert bob.get(f"{API}/tracks/{first_b['id']}").json()["is_default"] is True


def test_deleting_the_default_track_promotes_within_the_same_user(
    alice: TestClient, bob: TestClient
) -> None:
    a1 = create_track(alice, "A1")
    create_track(alice, "A2")
    create_track(bob, "B1")
    create_track(bob, "B2")

    alice.delete(f"{API}/tracks/{a1['id']}")

    assert [(t["name"], t["is_default"]) for t in alice.get(f"{API}/tracks").json()] == [
        ("A2", True)
    ]
    assert [(t["name"], t["is_default"]) for t in bob.get(f"{API}/tracks").json()] == [
        ("B1", True),
        ("B2", False),
    ]


def test_the_only_track_rule_is_per_user(alice: TestClient, bob: TestClient) -> None:
    a = create_track(alice, "A")
    create_track(bob, "B1")
    create_track(bob, "B2")

    assert alice.delete(f"{API}/tracks/{a['id']}").status_code == 409


# --- other people's resources look like they do not exist ---


def test_other_users_tracks_are_not_found(bob: TestClient, alices: dict) -> None:
    track_id = alices["track"]["id"]

    assert bob.get(f"{API}/tracks/{track_id}").status_code == 404
    assert bob.patch(f"{API}/tracks/{track_id}", json={"name": "mine now"}).status_code == 404
    assert bob.delete(f"{API}/tracks/{track_id}").status_code == 404
    assert bob.get(f"{API}/tracks/{track_id}/event-types").status_code == 404
    assert (
        bob.post(
            f"{API}/tracks/{track_id}/event-types", json={"name": "Spy", "color": "#000000"}
        ).status_code
        == 404
    )
    assert (
        bob.put(f"{API}/tracks/{track_id}/event-types/order", json={"ids": []}).status_code == 404
    )
    assert bob.get(f"{API}/stats", params={"track_id": track_id}).status_code == 404
    assert bob.get(f"{API}/entries", params={"track_id": track_id}).status_code == 404


def test_other_users_event_types_are_not_found(bob: TestClient, alices: dict) -> None:
    type_id = alices["event_type"]["id"]

    assert bob.patch(f"{API}/event-types/{type_id}", json={"name": "Hacked"}).status_code == 404
    assert bob.delete(f"{API}/event-types/{type_id}").status_code == 404


def test_other_users_entries_are_not_found(bob: TestClient, alices: dict) -> None:
    entry_id = alices["entry"]["id"]

    assert bob.get(f"{API}/entries/{entry_id}").status_code == 404
    assert bob.patch(f"{API}/entries/{entry_id}", json={"note": "mine"}).status_code == 404
    assert bob.delete(f"{API}/entries/{entry_id}").status_code == 404


def test_you_cannot_log_an_entry_on_somebody_elses_event_type(
    alice: TestClient, bob: TestClient, alices: dict
) -> None:
    response = bob.post(
        f"{API}/entries",
        json={"event_type_id": alices["event_type"]["id"], "date": "2026-11-05"},
    )

    assert response.status_code == 422
    assert [e["note"] for e in alice.get(f"{API}/entries").json()] == ["secret note"]


def test_you_cannot_move_an_entry_to_somebody_elses_event_type(
    alice: TestClient, bob: TestClient, alices: dict
) -> None:
    bob_track = create_track(bob, "B")
    bob_type = create_event_type(bob, bob_track["id"], "Reading")
    bob_entry = create_entry(bob, bob_type["id"], "2026-11-03")

    response = bob.patch(
        f"{API}/entries/{bob_entry['id']}", json={"event_type_id": alices["event_type"]["id"]}
    )

    assert response.status_code == 422
    assert bob.get(f"{API}/entries/{bob_entry['id']}").json()["event_type_id"] == bob_type["id"]


def test_reordering_with_somebody_elses_ids_is_rejected(
    alice: TestClient, bob: TestClient, alices: dict
) -> None:
    mine = create_track(bob, "B")

    response = bob.put(f"{API}/tracks/order", json={"ids": [mine["id"], alices["track"]["id"]]})

    assert response.status_code == 422
    assert [t["name"] for t in alice.get(f"{API}/tracks").json()] == ["Alice's track"]


def test_nothing_changed_for_the_owner_after_all_those_attempts(
    alice: TestClient, bob: TestClient, alices: dict
) -> None:
    track_id, type_id, entry_id = (
        alices["track"]["id"],
        alices["event_type"]["id"],
        alices["entry"]["id"],
    )
    bob.patch(f"{API}/tracks/{track_id}", json={"name": "x"})
    bob.delete(f"{API}/tracks/{track_id}")
    bob.patch(f"{API}/event-types/{type_id}", json={"name": "x"})
    bob.delete(f"{API}/event-types/{type_id}")
    bob.patch(f"{API}/entries/{entry_id}", json={"note": "x"})
    bob.delete(f"{API}/entries/{entry_id}")

    assert alice.get(f"{API}/tracks/{track_id}").json()["name"] == "Alice's track"
    assert alice.get(f"{API}/tracks/{track_id}/event-types").json()[0]["name"] == "Running"
    assert alice.get(f"{API}/entries/{entry_id}").json()["note"] == "secret note"


# --- statistics, export and import ---


def test_statistics_are_computed_from_your_data_only(
    alice: TestClient, bob: TestClient, alices: dict
) -> None:
    mine = create_track(bob, "B")
    create_event_type(bob, mine["id"], "Reading")

    stats = bob.get(f"{API}/stats", params={"track_id": mine["id"], "period": "all"}).json()

    assert [t["name"] for t in stats["event_types"]] == ["Reading"]
    assert stats["heatmap"] == []


def test_export_contains_only_your_data(alice: TestClient, bob: TestClient, alices: dict) -> None:
    create_track(bob, "Bob's track")

    alice_export = alice.get(f"{API}/export").json()
    bob_export = bob.get(f"{API}/export").json()

    assert [t["name"] for t in alice_export["tracks"]] == ["Alice's track"]
    assert [t["name"] for t in bob_export["tracks"]] == ["Bob's track"]
    assert "secret note" not in str(bob_export)


def test_import_only_replaces_your_own_data(
    alice: TestClient, bob: TestClient, alices: dict
) -> None:
    create_track(bob, "Old Bob")
    document = {"tracks": [{"name": "New Bob", "is_default": True}]}

    assert bob.post(f"{API}/import", json=document).status_code == 204

    assert [t["name"] for t in bob.get(f"{API}/tracks").json()] == ["New Bob"]
    assert [t["name"] for t in alice.get(f"{API}/tracks").json()] == ["Alice's track"]
    assert [e["note"] for e in alice.get(f"{API}/entries").json()] == ["secret note"]


def test_a_failed_import_leaves_everyone_untouched(
    alice: TestClient, bob: TestClient, alices: dict
) -> None:
    create_track(bob, "Bob")

    assert bob.post(f"{API}/import", json={"tracks": []}).status_code == 422

    assert len(bob.get(f"{API}/tracks").json()) == 1
    assert len(alice.get(f"{API}/tracks").json()) == 1


def test_one_users_export_can_be_imported_by_another(
    alice: TestClient, bob: TestClient, alices: dict
) -> None:
    exported = alice.get(f"{API}/export").json()

    assert bob.post(f"{API}/import", json=exported).status_code == 204

    bob_entries = bob.get(f"{API}/entries").json()
    assert [e["note"] for e in bob_entries] == ["secret note"]
    assert bob_entries[0]["id"] != alices["entry"]["id"], "the copy is a new, separate entry"
    bob.delete(f"{API}/entries/{bob_entries[0]['id']}")
    assert len(alice.get(f"{API}/entries").json()) == 1


# --- sessions do not mix ---


def test_signing_in_as_another_user_on_the_same_client_switches_data(
    sign_in: Callable[..., TestClient], alices: dict
) -> None:
    client = sign_in("bob")
    assert client.get(f"{API}/tracks").json() == []

    client.post(f"{API}/auth/logout")
    response = client.post(
        f"{API}/auth/login", json={"username": "alice", "password": "correct horse battery"}
    )

    assert response.status_code == 200
    assert [t["name"] for t in client.get(f"{API}/tracks").json()] == ["Alice's track"]
