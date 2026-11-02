import pytest
from fastapi.testclient import TestClient

from tests.helpers import API, create_entry, create_event_type, create_track


@pytest.fixture
def track(client: TestClient) -> dict:
    return create_track(client)


def test_create_applies_defaults_and_normalizes_color(client: TestClient, track: dict) -> None:
    event_type = create_event_type(client, track["id"], color="#FF00AA")

    assert event_type["color"] == "#ff00aa"
    assert event_type["icon_kind"] == "none"
    assert event_type["icon_value"] == ""
    assert event_type["entry_count"] == 0
    assert event_type["track_id"] == track["id"]


@pytest.mark.parametrize("color", ["red", "#fff", "ff0000", "#gg0000", "#ff00000"])
def test_invalid_color_is_rejected(client: TestClient, track: dict, color: str) -> None:
    response = client.post(
        f"{API}/tracks/{track['id']}/event-types", json={"name": "X", "color": color}
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("kind", "value"),
    [("emoji", "🏃"), ("emoji", "★"), ("text", "R"), ("text", "7"), ("text", "12"), ("none", "")],
)
def test_valid_icons(client: TestClient, track: dict, kind: str, value: str) -> None:
    event_type = create_event_type(client, track["id"], icon_kind=kind, icon_value=value)

    assert (event_type["icon_kind"], event_type["icon_value"]) == (kind, value)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("none", "x"),
        ("emoji", ""),
        ("emoji", "abc"),
        ("emoji", "🏃 🏃"),
        ("text", ""),
        ("text", "abc"),
        ("text", "🏃"),
        ("image", "x"),
    ],
)
def test_invalid_icons(client: TestClient, track: dict, kind: str, value: str) -> None:
    response = client.post(
        f"{API}/tracks/{track['id']}/event-types",
        json={"name": "X", "color": "#000000", "icon_kind": kind, "icon_value": value},
    )

    assert response.status_code == 422


def test_list_is_ordered_and_reports_entry_counts(client: TestClient, track: dict) -> None:
    run = create_event_type(client, track["id"], "Run")
    swim = create_event_type(client, track["id"], "Swim")
    create_entry(client, swim["id"], "2026-11-01")
    create_entry(client, swim["id"], "2026-11-01")

    listing = client.get(f"{API}/tracks/{track['id']}/event-types").json()

    assert [(et["name"], et["entry_count"]) for et in listing] == [("Run", 0), ("Swim", 2)]
    assert run["position"] < swim["position"]


def test_event_types_belong_to_one_track(client: TestClient, track: dict) -> None:
    other = create_track(client, "Other")
    create_event_type(client, other["id"], "Elsewhere")

    assert client.get(f"{API}/tracks/{track['id']}/event-types").json() == []


def test_unknown_track_is_404(client: TestClient) -> None:
    assert client.get(f"{API}/tracks/999/event-types").status_code == 404
    response = client.post(f"{API}/tracks/999/event-types", json={"name": "X", "color": "#000000"})
    assert response.status_code == 404


def test_partial_update(client: TestClient, track: dict) -> None:
    event_type = create_event_type(client, track["id"], icon_kind="text", icon_value="R")

    response = client.patch(f"{API}/event-types/{event_type['id']}", json={"name": "Jog"})

    body = response.json()
    assert response.status_code == 200
    assert (body["name"], body["color"], body["icon_value"]) == ("Jog", "#ff0000", "R")


def test_update_icon_must_stay_consistent(client: TestClient, track: dict) -> None:
    event_type = create_event_type(client, track["id"], icon_kind="text", icon_value="R")
    url = f"{API}/event-types/{event_type['id']}"

    assert client.patch(url, json={"icon_kind": "none"}).status_code == 422
    assert client.patch(url, json={"icon_kind": "none", "icon_value": ""}).status_code == 200
    assert client.patch(url, json={"icon_kind": "emoji"}).status_code == 422
    assert client.patch(url, json={"icon_kind": "emoji", "icon_value": "🏃"}).status_code == 200


def test_update_reports_entry_count(client: TestClient, track: dict) -> None:
    event_type = create_event_type(client, track["id"])
    create_entry(client, event_type["id"], "2026-11-02")

    response = client.patch(f"{API}/event-types/{event_type['id']}", json={"name": "Jog"})

    assert response.json()["entry_count"] == 1


def test_reorder(client: TestClient, track: dict) -> None:
    a = create_event_type(client, track["id"], "A")
    b = create_event_type(client, track["id"], "B")

    response = client.put(
        f"{API}/tracks/{track['id']}/event-types/order", json={"ids": [b["id"], a["id"]]}
    )

    assert [et["name"] for et in response.json()] == ["B", "A"]
    assert (
        client.put(
            f"{API}/tracks/{track['id']}/event-types/order", json={"ids": [a["id"]]}
        ).status_code
        == 422
    )


def test_delete_removes_its_entries_only(client: TestClient, track: dict) -> None:
    keep = create_event_type(client, track["id"], "Keep")
    drop = create_event_type(client, track["id"], "Drop")
    create_entry(client, keep["id"], "2026-11-02")
    create_entry(client, drop["id"], "2026-11-02")
    create_entry(client, drop["id"], "2026-11-03")

    response = client.delete(f"{API}/event-types/{drop['id']}")

    assert response.status_code == 204
    entries = client.get(f"{API}/entries").json()
    assert [e["event_type_id"] for e in entries] == [keep["id"]]


def test_unknown_event_type_is_404(client: TestClient) -> None:
    assert client.patch(f"{API}/event-types/999", json={"name": "x"}).status_code == 404
    assert client.delete(f"{API}/event-types/999").status_code == 404
