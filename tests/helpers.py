from fastapi.testclient import TestClient

API = "/api/v1"


def create_track(client: TestClient, name: str = "Workout") -> dict:
    response = client.post(f"{API}/tracks", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def create_event_type(
    client: TestClient, track_id: int, name: str = "Running", color: str = "#ff0000", **extra
) -> dict:
    response = client.post(
        f"{API}/tracks/{track_id}/event-types", json={"name": name, "color": color, **extra}
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_entry(
    client: TestClient, event_type_id: int, date: str, note: str | None = None
) -> dict:
    response = client.post(
        f"{API}/entries", json={"event_type_id": event_type_id, "date": date, "note": note}
    )
    assert response.status_code == 201, response.text
    return response.json()
