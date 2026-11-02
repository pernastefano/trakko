import copy

import pytest
from fastapi.testclient import TestClient

from tests.helpers import API, create_entry, create_event_type, create_track


def populate(client: TestClient) -> None:
    cycle = create_track(client, "Cycle")
    workout = create_track(client, "Workout")
    start = create_event_type(
        client, cycle["id"], "Start", "#aa0000", icon_kind="text", icon_value="S"
    )
    end = create_event_type(client, cycle["id"], "End", "#00aa00")
    run = create_event_type(
        client, workout["id"], "Run", "#0000aa", icon_kind="emoji", icon_value="🏃"
    )
    create_entry(client, start["id"], "2026-10-01", "first")
    create_entry(client, end["id"], "2026-10-06")
    create_entry(client, run["id"], "2026-11-02")
    create_entry(client, run["id"], "2026-11-02", "second run")
    client.patch(f"{API}/tracks/{workout['id']}", json={"is_default": True})


def snapshot(client: TestClient) -> dict:
    body = client.get(f"{API}/export").json()
    body.pop("exported_at")
    return body


def test_export_structure(client: TestClient) -> None:
    populate(client)

    body = client.get(f"{API}/export").json()

    assert body["version"] == 1
    assert body["exported_at"]
    assert [t["name"] for t in body["tracks"]] == ["Cycle", "Workout"]
    assert [t["is_default"] for t in body["tracks"]] == [False, True]
    cycle_types = body["tracks"][0]["event_types"]
    assert [et["name"] for et in cycle_types] == ["Start", "End"]
    assert cycle_types[0]["icon_kind"] == "text"
    assert cycle_types[0]["entries"][0]["date"] == "2026-10-01"
    assert cycle_types[0]["entries"][0]["note"] == "first"
    assert "id" not in body["tracks"][0]
    assert body["tracks"][0]["event_types"][0]["entries"][0]["created_at"].endswith("Z")


def test_round_trip_restores_the_exported_state(client: TestClient) -> None:
    populate(client)
    exported = client.get(f"{API}/export").json()
    before = snapshot(client)
    wipe = {"tracks": [{"name": "Blank", "is_default": True}]}
    assert client.post(f"{API}/import", json=wipe).status_code == 204
    assert client.get(f"{API}/entries").json() == []

    response = client.post(f"{API}/import", json=exported)

    assert response.status_code == 204
    assert snapshot(client) == before


def test_import_replaces_existing_data(client: TestClient) -> None:
    populate(client)
    exported = client.get(f"{API}/export").json()
    extra = create_track(client, "Extra")
    create_event_type(client, extra["id"], "Extra type")

    client.post(f"{API}/import", json=exported)

    assert [t["name"] for t in client.get(f"{API}/tracks").json()] == ["Cycle", "Workout"]
    assert len(client.get(f"{API}/entries").json()) == 4


def test_import_assigns_fresh_ids_and_keeps_order(client: TestClient) -> None:
    populate(client)
    exported = client.get(f"{API}/export").json()

    client.post(f"{API}/import", json=exported)

    tracks = client.get(f"{API}/tracks").json()
    assert [t["position"] for t in tracks] == [0, 1]
    types = client.get(f"{API}/tracks/{tracks[0]['id']}/event-types").json()
    assert [(et["name"], et["position"], et["entry_count"]) for et in types] == [
        ("Start", 0, 1),
        ("End", 1, 1),
    ]


def test_import_minimal_document_applies_defaults(client: TestClient) -> None:
    document = {
        "tracks": [
            {
                "name": "Only",
                "is_default": True,
                "event_types": [
                    {
                        "name": "Thing",
                        "color": "#ABCDEF",
                        "entries": [{"date": "2026-11-02"}, {"date": "2026-11-03", "note": " n "}],
                    }
                ],
            }
        ]
    }

    assert client.post(f"{API}/import", json=document).status_code == 204

    entries = client.get(f"{API}/entries").json()
    assert [(e["date"], e["note"]) for e in entries] == [("2026-11-02", None), ("2026-11-03", "n")]
    assert entries[0]["created_at"]
    track_id = client.get(f"{API}/tracks").json()[0]["id"]
    assert client.get(f"{API}/tracks/{track_id}/event-types").json()[0]["color"] == "#abcdef"


def valid_document() -> dict:
    return {
        "version": 1,
        "tracks": [
            {
                "name": "T",
                "is_default": True,
                "event_types": [
                    {"name": "E", "color": "#000000", "entries": [{"date": "2026-11-02"}]}
                ],
            }
        ],
    }


def broken(change) -> dict:
    document = copy.deepcopy(valid_document())
    change(document)
    return document


INVALID_DOCUMENTS = {
    "no tracks": broken(lambda d: d.update(tracks=[])),
    "no default": broken(lambda d: d["tracks"][0].update(is_default=False)),
    "two defaults": broken(lambda d: d["tracks"].append({"name": "U", "is_default": True})),
    "wrong version": broken(lambda d: d.update(version=2)),
    "bad color": broken(lambda d: d["tracks"][0]["event_types"][0].update(color="red")),
    "bad icon": broken(lambda d: d["tracks"][0]["event_types"][0].update(icon_kind="emoji")),
    "bad date": broken(lambda d: d["tracks"][0]["event_types"][0]["entries"][0].update(date="x")),
    "long note": broken(
        lambda d: d["tracks"][0]["event_types"][0]["entries"][0].update(note="x" * 281)
    ),
    "blank track name": broken(lambda d: d["tracks"][0].update(name=" ")),
}


@pytest.mark.parametrize("document", INVALID_DOCUMENTS.values(), ids=INVALID_DOCUMENTS.keys())
def test_invalid_import_is_rejected_and_keeps_existing_data(
    client: TestClient, document: dict
) -> None:
    populate(client)
    before = snapshot(client)

    response = client.post(f"{API}/import", json=document)

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert snapshot(client) == before


def test_valid_document_fixture_is_actually_valid(client: TestClient) -> None:
    assert client.post(f"{API}/import", json=valid_document()).status_code == 204
