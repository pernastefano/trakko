import pytest
from fastapi.testclient import TestClient

from tests.helpers import API, create_entry, create_event_type, create_track


@pytest.fixture
def event_type(client: TestClient) -> dict:
    return create_event_type(client, create_track(client)["id"])


def test_create_entry(client: TestClient, event_type: dict) -> None:
    entry = create_entry(client, event_type["id"], "2026-11-02", "Easy 5k")

    assert entry["date"] == "2026-11-02"
    assert entry["note"] == "Easy 5k"
    assert entry["created_at"].endswith("Z") and entry["updated_at"].endswith("Z")
    assert client.get(f"{API}/entries/{entry['id']}").json() == entry


def test_note_is_optional_trimmed_and_blank_becomes_null(
    client: TestClient, event_type: dict
) -> None:
    assert create_entry(client, event_type["id"], "2026-11-02")["note"] is None
    assert create_entry(client, event_type["id"], "2026-11-02", "   ")["note"] is None
    assert create_entry(client, event_type["id"], "2026-11-02", "  hi  ")["note"] == "hi"


def test_note_length_limit(client: TestClient, event_type: dict) -> None:
    assert create_entry(client, event_type["id"], "2026-11-02", "x" * 280)["note"] == "x" * 280

    response = client.post(
        f"{API}/entries",
        json={"event_type_id": event_type["id"], "date": "2026-11-02", "note": "x" * 281},
    )

    assert response.status_code == 422
    assert "280" in response.json()["detail"]


@pytest.mark.parametrize("date", ["2026-13-01", "2026-02-30", "02/11/2026", "20261102", 1700000000])
def test_invalid_dates_are_rejected(client: TestClient, event_type: dict, date: object) -> None:
    response = client.post(f"{API}/entries", json={"event_type_id": event_type["id"], "date": date})

    assert response.status_code == 422


def test_unknown_event_type_is_rejected(client: TestClient) -> None:
    response = client.post(f"{API}/entries", json={"event_type_id": 999, "date": "2026-11-02"})

    assert response.status_code == 422
    assert "event_type_id" in response.json()["detail"]


def test_same_day_and_same_type_can_repeat(client: TestClient, event_type: dict) -> None:
    create_entry(client, event_type["id"], "2026-11-02")
    create_entry(client, event_type["id"], "2026-11-02")

    assert len(client.get(f"{API}/entries").json()) == 2


def test_list_filters(client: TestClient) -> None:
    track_a = create_track(client, "A")
    track_b = create_track(client, "B")
    run = create_event_type(client, track_a["id"], "Run")
    swim = create_event_type(client, track_a["id"], "Swim")
    other = create_event_type(client, track_b["id"], "Other")
    create_entry(client, run["id"], "2026-10-31")
    create_entry(client, run["id"], "2026-11-02")
    create_entry(client, swim["id"], "2026-11-15")
    create_entry(client, other["id"], "2026-11-02")

    def dates(**params: object) -> list[str]:
        response = client.get(f"{API}/entries", params=params)
        assert response.status_code == 200, response.text
        return [e["date"] for e in response.json()]

    assert len(dates()) == 4
    assert dates(track_id=track_a["id"]) == ["2026-10-31", "2026-11-02", "2026-11-15"]
    assert dates(track_id=track_b["id"]) == ["2026-11-02"]
    assert dates(event_type_id=swim["id"]) == ["2026-11-15"]
    assert dates(track_id=track_a["id"], **{"from": "2026-11-01", "to": "2026-11-30"}) == [
        "2026-11-02",
        "2026-11-15",
    ]
    assert dates(track_id=track_a["id"], **{"to": "2026-10-31"}) == ["2026-10-31"]
    assert dates(track_id=track_a["id"], **{"from": "2026-11-02", "to": "2026-11-02"}) == [
        "2026-11-02"
    ]


def test_list_is_sorted_by_date_then_id(client: TestClient, event_type: dict) -> None:
    later = create_entry(client, event_type["id"], "2026-11-03")
    first = create_entry(client, event_type["id"], "2026-11-01")
    second = create_entry(client, event_type["id"], "2026-11-01")

    ids = [e["id"] for e in client.get(f"{API}/entries").json()]

    assert ids == [first["id"], second["id"], later["id"]]


def test_list_rejects_inverted_range_unknown_track_and_bad_dates(client: TestClient) -> None:
    create_track(client)

    inverted = client.get(f"{API}/entries", params={"from": "2026-11-02", "to": "2026-11-01"})
    assert inverted.status_code == 422
    assert client.get(f"{API}/entries", params={"track_id": 999}).status_code == 404
    assert client.get(f"{API}/entries", params={"from": "1700000000"}).status_code == 422


def test_update_note_date_and_type(client: TestClient) -> None:
    track = create_track(client)
    run = create_event_type(client, track["id"], "Run")
    swim = create_event_type(client, track["id"], "Swim")
    entry = create_entry(client, run["id"], "2026-11-02", "old")

    response = client.patch(
        f"{API}/entries/{entry['id']}",
        json={"note": "new", "date": "2026-11-03", "event_type_id": swim["id"]},
    )

    body = response.json()
    assert response.status_code == 200
    assert (body["note"], body["date"], body["event_type_id"]) == ("new", "2026-11-03", swim["id"])


def test_update_leaves_unsent_fields_and_null_clears_note(
    client: TestClient, event_type: dict
) -> None:
    entry = create_entry(client, event_type["id"], "2026-11-02", "keep me")
    url = f"{API}/entries/{entry['id']}"

    after_date = client.patch(url, json={"date": "2026-11-05"}).json()
    assert (after_date["note"], after_date["date"]) == ("keep me", "2026-11-05")

    cleared = client.patch(url, json={"note": None}).json()
    assert cleared["note"] is None
    assert cleared["date"] == "2026-11-05"


def test_entry_cannot_move_to_another_track(client: TestClient) -> None:
    run = create_event_type(client, create_track(client, "A")["id"])
    foreign = create_event_type(client, create_track(client, "B")["id"])
    entry = create_entry(client, run["id"], "2026-11-02")

    response = client.patch(f"{API}/entries/{entry['id']}", json={"event_type_id": foreign["id"]})

    assert response.status_code == 422
    assert client.get(f"{API}/entries/{entry['id']}").json()["event_type_id"] == run["id"]


def test_delete(client: TestClient, event_type: dict) -> None:
    entry = create_entry(client, event_type["id"], "2026-11-02")

    assert client.delete(f"{API}/entries/{entry['id']}").status_code == 204
    assert client.get(f"{API}/entries/{entry['id']}").status_code == 404


def test_unknown_entry_is_404(client: TestClient) -> None:
    assert client.get(f"{API}/entries/999").json() == {"detail": "Entry not found"}
    assert client.patch(f"{API}/entries/999", json={"note": "x"}).status_code == 404
    assert client.delete(f"{API}/entries/999").status_code == 404
