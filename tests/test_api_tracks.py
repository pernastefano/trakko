from fastapi.testclient import TestClient

from tests.helpers import API, create_entry, create_event_type, create_track


def test_first_track_is_default_and_next_ones_are_not(client: TestClient) -> None:
    first = create_track(client, "First")
    second = create_track(client, "Second")

    assert first["is_default"] is True
    assert second["is_default"] is False
    assert (first["position"], second["position"]) == (0, 1)


def test_list_is_ordered_by_position(client: TestClient) -> None:
    create_track(client, "A")
    create_track(client, "B")

    names = [track["name"] for track in client.get(f"{API}/tracks").json()]

    assert names == ["A", "B"]


def test_name_is_trimmed_and_must_not_be_blank(client: TestClient) -> None:
    assert create_track(client, "  Gym  ")["name"] == "Gym"

    response = client.post(f"{API}/tracks", json={"name": "   "})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert "name" in response.json()["detail"]


def test_rename(client: TestClient) -> None:
    track = create_track(client, "Old")

    response = client.patch(f"{API}/tracks/{track['id']}", json={"name": "New"})

    assert response.status_code == 200
    assert response.json()["name"] == "New"


def test_set_default_moves_the_flag(client: TestClient) -> None:
    first = create_track(client, "First")
    second = create_track(client, "Second")

    response = client.patch(f"{API}/tracks/{second['id']}", json={"is_default": True})

    assert response.json()["is_default"] is True
    defaults = {t["name"]: t["is_default"] for t in client.get(f"{API}/tracks").json()}
    assert defaults == {"First": False, "Second": True}
    assert first["id"] != second["id"]


def test_default_cannot_be_unset_directly(client: TestClient) -> None:
    track = create_track(client)

    response = client.patch(f"{API}/tracks/{track['id']}", json={"is_default": False})

    assert response.status_code == 422


def test_reorder(client: TestClient) -> None:
    a, b, c = (create_track(client, name) for name in "ABC")

    response = client.put(f"{API}/tracks/order", json={"ids": [c["id"], a["id"], b["id"]]})

    assert response.status_code == 200
    assert [t["name"] for t in response.json()] == ["C", "A", "B"]
    assert [t["name"] for t in client.get(f"{API}/tracks").json()] == ["C", "A", "B"]


def test_reorder_requires_every_track_exactly_once(client: TestClient) -> None:
    a = create_track(client, "A")
    create_track(client, "B")

    assert client.put(f"{API}/tracks/order", json={"ids": [a["id"]]}).status_code == 422
    assert client.put(f"{API}/tracks/order", json={"ids": [a["id"], a["id"]]}).status_code == 422
    assert client.put(f"{API}/tracks/order", json={"ids": [a["id"], 999]}).status_code == 422


def test_delete_track_cascades_to_event_types_and_entries(client: TestClient) -> None:
    keep = create_track(client, "Keep")
    drop = create_track(client, "Drop")
    event_type = create_event_type(client, drop["id"])
    create_entry(client, event_type["id"], "2026-11-02")

    response = client.delete(f"{API}/tracks/{drop['id']}")

    assert response.status_code == 204
    assert client.get(f"{API}/entries").json() == []
    assert client.get(f"{API}/tracks/{drop['id']}/event-types").status_code == 404
    assert [t["id"] for t in client.get(f"{API}/tracks").json()] == [keep["id"]]


def test_deleting_the_default_promotes_the_first_remaining_track(client: TestClient) -> None:
    default = create_track(client, "Default")
    create_track(client, "Second")
    create_track(client, "Third")

    client.delete(f"{API}/tracks/{default['id']}")

    tracks = client.get(f"{API}/tracks").json()
    assert [(t["name"], t["is_default"]) for t in tracks] == [
        ("Second", True),
        ("Third", False),
    ]


def test_the_only_track_cannot_be_deleted(client: TestClient) -> None:
    track = create_track(client)

    response = client.delete(f"{API}/tracks/{track['id']}")

    assert response.status_code == 409
    assert response.json() == {"detail": "The only Track cannot be deleted"}


def test_unknown_track_is_404(client: TestClient) -> None:
    for response in (
        client.get(f"{API}/tracks/999"),
        client.patch(f"{API}/tracks/999", json={"name": "x"}),
        client.delete(f"{API}/tracks/999"),
    ):
        assert response.status_code == 404
        assert response.json() == {"detail": "Track not found"}
