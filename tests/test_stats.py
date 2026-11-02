import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app.services.stats import average_interval, compute_streaks, period_range
from tests.helpers import API, create_entry, create_event_type, create_track


def days(*isos: str) -> list[dt.date]:
    return [dt.date.fromisoformat(iso) for iso in isos]


REF = dt.date(2026, 11, 10)


# --- pure functions ---


def test_streaks_with_no_days() -> None:
    assert compute_streaks([], REF) == (0, 0)


def test_streak_ending_today_or_yesterday_is_current() -> None:
    assert compute_streaks(days("2026-11-08", "2026-11-09", "2026-11-10"), REF) == (3, 3)
    assert compute_streaks(days("2026-11-08", "2026-11-09"), REF) == (2, 2)


def test_streak_is_broken_after_a_missed_day() -> None:
    assert compute_streaks(days("2026-11-07", "2026-11-08"), REF) == (0, 2)


def test_longest_streak_may_be_in_the_past() -> None:
    history = days("2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-11-10")

    assert compute_streaks(history, REF) == (1, 4)


def test_future_days_do_not_extend_the_current_streak() -> None:
    assert compute_streaks(days("2026-11-10", "2026-11-11", "2026-11-12"), REF) == (1, 3)


def test_streaks_across_month_and_leap_boundaries() -> None:
    assert compute_streaks(days("2028-02-28", "2028-02-29", "2028-03-01"), dt.date(2028, 3, 1)) == (
        3,
        3,
    )


def test_average_interval() -> None:
    assert average_interval([]) is None
    assert average_interval(days("2026-11-01")) is None
    assert average_interval(days("2026-10-01", "2026-10-29", "2026-11-26")) == 28
    assert average_interval(days("2026-11-01", "2026-11-02", "2026-11-05")) == 2


def test_period_range() -> None:
    assert period_range("month", dt.date(2028, 2, 10)) == (
        dt.date(2028, 2, 1),
        dt.date(2028, 2, 29),
    )
    assert period_range("year", dt.date(2026, 6, 1)) == (dt.date(2026, 1, 1), dt.date(2026, 12, 31))
    assert period_range("all", REF) == (None, None)


# --- API ---


@pytest.fixture
def setup(client: TestClient) -> dict:
    track = create_track(client)
    cycle = create_event_type(client, track["id"], "Cycle Start", "#ff0000")
    run = create_event_type(client, track["id"], "Run", "#00ff00")
    for day in ("2026-09-01", "2026-09-29", "2026-10-27"):
        create_entry(client, cycle["id"], day)
    for day in ("2026-11-02", "2026-11-02", "2026-11-09", "2026-11-10"):
        create_entry(client, run["id"], day)
    return {"track": track, "cycle": cycle, "run": run}


def stats(client: TestClient, track_id: int, **params: object) -> dict:
    response = client.get(
        f"{API}/stats", params={"track_id": track_id, "ref": "2026-11-10", **params}
    )
    assert response.status_code == 200, response.text
    return response.json()


def by_name(body: dict) -> dict:
    return {et["name"]: et for et in body["event_types"]}


def test_month_period(client: TestClient, setup: dict) -> None:
    body = stats(client, setup["track"]["id"], period="month")
    types = by_name(body)

    assert (body["start"], body["end"], body["granularity"]) == ("2026-11-01", "2026-11-30", "week")
    assert types["Run"]["count"] == 4
    assert types["Cycle Start"]["count"] == 0
    assert sum(b["count"] for b in body["buckets"]) == 4
    assert body["heatmap"] == [
        {"date": "2026-11-02", "count": 2},
        {"date": "2026-11-09", "count": 1},
        {"date": "2026-11-10", "count": 1},
    ]


def test_month_buckets_are_iso_weeks_starting_monday(client: TestClient, setup: dict) -> None:
    body = stats(client, setup["track"]["id"], period="month")

    starts = [b["start"] for b in body["buckets"]]
    assert starts == [
        "2026-10-26",
        "2026-11-02",
        "2026-11-09",
        "2026-11-16",
        "2026-11-23",
        "2026-11-30",
    ]
    assert [b["count"] for b in body["buckets"]] == [0, 2, 2, 0, 0, 0]


def test_year_period_uses_monthly_buckets(client: TestClient, setup: dict) -> None:
    body = stats(client, setup["track"]["id"], period="year")
    counts = {b["start"]: b["count"] for b in body["buckets"]}

    assert (body["start"], body["end"], body["granularity"]) == (
        "2026-01-01",
        "2026-12-31",
        "month",
    )
    assert len(body["buckets"]) == 12
    assert (counts["2026-09-01"], counts["2026-10-01"], counts["2026-11-01"]) == (2, 1, 4)
    assert counts["2026-01-01"] == 0
    assert by_name(body)["Cycle Start"]["count"] == 3


def test_all_period_spans_first_to_last_entry(client: TestClient, setup: dict) -> None:
    body = stats(client, setup["track"]["id"], period="all")

    assert (body["start"], body["end"]) == ("2026-09-01", "2026-11-10")
    assert [b["start"] for b in body["buckets"]] == ["2026-09-01", "2026-10-01", "2026-11-01"]
    assert sum(item["count"] for item in body["heatmap"]) == 7


def test_per_type_metrics_use_the_whole_history(client: TestClient, setup: dict) -> None:
    types = by_name(stats(client, setup["track"]["id"], period="month"))

    cycle, run = types["Cycle Start"], types["Run"]
    assert cycle["last_date"] == "2026-10-27"
    assert cycle["days_since_last"] == 14
    assert cycle["average_interval_days"] == 28
    assert (cycle["current_streak"], cycle["longest_streak"]) == (0, 1)
    assert run["last_date"] == "2026-11-10"
    assert run["days_since_last"] == 0
    assert run["average_interval_days"] == pytest.approx(4.0)
    assert (run["current_streak"], run["longest_streak"]) == (2, 2)


def test_event_type_without_entries(client: TestClient) -> None:
    track = create_track(client)
    create_event_type(client, track["id"], "Empty")

    body = stats(client, track["id"], period="all")

    empty = body["event_types"][0]
    assert empty["count"] == 0
    assert empty["last_date"] is None
    assert empty["days_since_last"] is None
    assert empty["average_interval_days"] is None
    assert (body["start"], body["end"], body["buckets"], body["heatmap"]) == (None, None, [], [])


def test_stats_are_scoped_to_the_track(client: TestClient, setup: dict) -> None:
    other = create_track(client, "Other")
    other_type = create_event_type(client, other["id"], "Other type")
    create_entry(client, other_type["id"], "2026-11-05")

    body = stats(client, other["id"], period="month")

    assert [et["name"] for et in body["event_types"]] == ["Other type"]
    assert sum(b["count"] for b in body["buckets"]) == 1


def test_defaults_and_validation(client: TestClient, setup: dict) -> None:
    track_id = setup["track"]["id"]

    assert client.get(f"{API}/stats", params={"track_id": track_id}).json()["period"] == "month"
    assert client.get(f"{API}/stats", params={"track_id": 999}).status_code == 404
    assert client.get(f"{API}/stats").status_code == 422
    assert (
        client.get(f"{API}/stats", params={"track_id": track_id, "period": "week"}).status_code
        == 422
    )
    assert (
        client.get(f"{API}/stats", params={"track_id": track_id, "ref": "nope"}).status_code == 422
    )
