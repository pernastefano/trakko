import datetime as dt
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base, make_engine, sqlite_url
from app.models import Entry, EventType, Track


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = make_engine(sqlite_url(str(tmp_path / "test.db")))
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_track(name: str = "Workout", *, is_default: bool = False) -> Track:
    return Track(name=name, is_default=is_default)


def make_event_type(track: Track, name: str = "Running") -> EventType:
    return EventType(track=track, name=name, color="#ff0000")


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_defaults_are_applied(session: Session) -> None:
    track = make_track()
    event_type = make_event_type(track)
    entry = Entry(event_type=event_type, date=dt.date(2026, 11, 2))
    session.add(track)
    session.commit()

    assert track.position == 0
    assert track.is_default is False
    assert event_type.icon_kind == "none"
    assert event_type.icon_value == ""
    assert entry.note is None
    assert entry.created_at is not None
    assert entry.updated_at is not None


def test_date_is_a_plain_calendar_date(session: Session) -> None:
    track = make_track()
    session.add(Entry(event_type=make_event_type(track), date=dt.date(2026, 2, 28)))
    session.commit()
    session.expire_all()

    assert session.scalars(select(Entry.date)).one() == dt.date(2026, 2, 28)


def test_multiple_entries_same_day_and_type(session: Session) -> None:
    event_type = make_event_type(make_track())
    day = dt.date(2026, 11, 2)
    session.add_all(
        [Entry(event_type=event_type, date=day), Entry(event_type=event_type, date=day)]
    )
    session.commit()

    assert count(session, Entry) == 2


def test_only_one_default_track(session: Session) -> None:
    session.add(make_track("A", is_default=True))
    session.commit()
    session.add(make_track("B", is_default=True))

    with pytest.raises(IntegrityError):
        session.commit()


def test_many_non_default_tracks_allowed(session: Session) -> None:
    session.add_all([make_track("A"), make_track("B"), make_track("C", is_default=True)])
    session.commit()

    assert count(session, Track) == 3


def test_invalid_icon_kind_rejected(session: Session) -> None:
    session.add(EventType(track=make_track(), name="X", color="#000000", icon_kind="image"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_note_longer_than_280_rejected(session: Session) -> None:
    event_type = make_event_type(make_track())
    session.add(Entry(event_type=event_type, date=dt.date(2026, 11, 2), note="x" * 281))

    with pytest.raises(IntegrityError):
        session.commit()


def test_note_of_280_accepted(session: Session) -> None:
    event_type = make_event_type(make_track())
    session.add(Entry(event_type=event_type, date=dt.date(2026, 11, 2), note="x" * 280))
    session.commit()

    assert count(session, Entry) == 1


def test_deleting_track_deletes_event_types_and_entries(session: Session) -> None:
    track = make_track()
    other = make_track("Other")
    for owner in (track, other):
        event_type = make_event_type(owner)
        session.add(Entry(event_type=event_type, date=dt.date(2026, 11, 2)))
    session.commit()

    session.delete(track)
    session.commit()

    assert count(session, Track) == 1
    assert count(session, EventType) == 1
    assert count(session, Entry) == 1


def test_deleting_event_type_deletes_its_entries(session: Session) -> None:
    track = make_track()
    keep = make_event_type(track, "Keep")
    drop = make_event_type(track, "Drop")
    session.add_all(
        [
            Entry(event_type=keep, date=dt.date(2026, 11, 2)),
            Entry(event_type=drop, date=dt.date(2026, 11, 2)),
            Entry(event_type=drop, date=dt.date(2026, 11, 3)),
        ]
    )
    session.commit()

    session.delete(drop)
    session.commit()

    assert count(session, EventType) == 1
    assert count(session, Entry) == 1


def test_database_level_cascade_without_orm(session: Session) -> None:
    track = make_track()
    session.add(Entry(event_type=make_event_type(track), date=dt.date(2026, 11, 2)))
    session.commit()

    session.execute(Track.__table__.delete())
    session.commit()

    assert count(session, EventType) == 0
    assert count(session, Entry) == 0


def test_event_types_are_ordered_by_position(session: Session) -> None:
    track = make_track()
    EventType(track=track, name="Second", color="#000000", position=1)
    EventType(track=track, name="First", color="#000000", position=0)
    session.add(track)
    session.commit()
    session.expire_all()

    assert [et.name for et in session.scalars(select(Track)).one().event_types] == [
        "First",
        "Second",
    ]
