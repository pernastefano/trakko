import re

from fastapi.testclient import TestClient

from app import __version__
from tests.helpers import API


def test_the_version_is_a_semantic_version() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__), __version__


def test_about_reports_the_name_and_version(client: TestClient) -> None:
    response = client.get(f"{API}/about")

    assert response.status_code == 200
    assert response.json() == {"name": "TRAKKO", "version": __version__}


def test_about_needs_a_signed_in_user(client_factory) -> None:
    response = client_factory().get(f"{API}/about")

    assert response.status_code == 401


def test_the_api_documentation_reports_the_same_version(client_factory) -> None:
    schema = client_factory().get("/openapi.json").json()

    assert schema["info"]["version"] == __version__


def test_health_is_unchanged(client_factory) -> None:
    assert client_factory().get("/health").json() == {"status": "ok"}
