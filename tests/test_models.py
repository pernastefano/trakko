import datetime as dt

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Entry, EventType, Track, User


@pytest.fixture
def owner(session: Session) -> User:
    user = User(username="alice", password_hash="not-a-real-hash")
    session.add(user)
    session.commit()
    return user


def make_track(owner: User, name: str = "Workout", *, is_default: bool = False) -> Track:
    return Track(user=owner, name=name, is_default=is_default)


def make_event_type(track: Track, name: str = "Running") -> EventType:
    return EventType(track=track, name=name, color="#ff0000")


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_defaults_are_applied(session: Session, owner: User) -> None:
    track = make_track(owner)
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


def test_date_is_a_plain_calendar_date(session: Session, owner: User) -> None:
    track = make_track(owner)
    session.add(Entry(event_type=make_event_type(track), date=dt.date(2026, 2, 28)))
    session.commit()
    session.expire_all()

    assert session.scalars(select(Entry.date)).one() == dt.date(2026, 2, 28)


def test_multiple_entries_same_day_and_type(session: Session, owner: User) -> None:
    event_type = make_event_type(make_track(owner))
    day = dt.date(2026, 11, 2)
    session.add_all(
        [Entry(event_type=event_type, date=day), Entry(event_type=event_type, date=day)]
    )
    session.commit()

    assert count(session, Entry) == 2


def test_only_one_default_track(session: Session, owner: User) -> None:
    session.add(make_track(owner, "A", is_default=True))
    session.commit()
    session.add(make_track(owner, "B", is_default=True))

    with pytest.raises(IntegrityError):
        session.commit()


def test_many_non_default_tracks_allowed(session: Session, owner: User) -> None:
    session.add_all(
        [make_track(owner, "A"), make_track(owner, "B"), make_track(owner, "C", is_default=True)]
    )
    session.commit()

    assert count(session, Track) == 3


def test_invalid_icon_kind_rejected(session: Session, owner: User) -> None:
    session.add(EventType(track=make_track(owner), name="X", color="#000000", icon_kind="image"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_note_longer_than_280_rejected(session: Session, owner: User) -> None:
    event_type = make_event_type(make_track(owner))
    session.add(Entry(event_type=event_type, date=dt.date(2026, 11, 2), note="x" * 281))

    with pytest.raises(IntegrityError):
        session.commit()


def test_note_of_280_accepted(session: Session, owner: User) -> None:
    event_type = make_event_type(make_track(owner))
    session.add(Entry(event_type=event_type, date=dt.date(2026, 11, 2), note="x" * 280))
    session.commit()

    assert count(session, Entry) == 1


def test_deleting_track_deletes_event_types_and_entries(session: Session, owner: User) -> None:
    track = make_track(owner)
    other = make_track(owner, "Other")
    for owner in (track, other):
        event_type = make_event_type(owner)
        session.add(Entry(event_type=event_type, date=dt.date(2026, 11, 2)))
    session.commit()

    session.delete(track)
    session.commit()

    assert count(session, Track) == 1
    assert count(session, EventType) == 1
    assert count(session, Entry) == 1


def test_deleting_event_type_deletes_its_entries(session: Session, owner: User) -> None:
    track = make_track(owner)
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


def test_database_level_cascade_without_orm(session: Session, owner: User) -> None:
    track = make_track(owner)
    session.add(Entry(event_type=make_event_type(track), date=dt.date(2026, 11, 2)))
    session.commit()

    session.execute(Track.__table__.delete())
    session.commit()

    assert count(session, EventType) == 0
    assert count(session, Entry) == 0


def test_event_types_are_ordered_by_position(session: Session, owner: User) -> None:
    track = make_track(owner)
    EventType(track=track, name="Second", color="#000000", position=1)
    EventType(track=track, name="First", color="#000000", position=0)
    session.add(track)
    session.commit()
    session.expire_all()

    assert [et.name for et in session.scalars(select(Track)).one().event_types] == [
        "First",
        "Second",
    ]


def test_each_user_can_have_one_default_track(session: Session, owner: User) -> None:
    other = User(username="bob", password_hash="not-a-real-hash")
    session.add_all([other, make_track(owner, "Mine", is_default=True)])
    session.add(make_track(other, "Theirs", is_default=True))
    session.commit()

    assert count(session, Track) == 2


def test_a_user_cannot_have_two_default_tracks(session: Session, owner: User) -> None:
    session.add_all(
        [make_track(owner, "A", is_default=True), make_track(owner, "B", is_default=True)]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_usernames_are_unique(session: Session, owner: User) -> None:
    session.add(User(username=owner.username, password_hash="x"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_track_needs_an_owner(session: Session) -> None:
    session.add(Track(name="Orphan"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_deleting_a_user_deletes_everything_they_own(session: Session, owner: User) -> None:
    other = User(username="bob", password_hash="x")
    session.add(other)
    for user in (owner, other):
        event_type = make_event_type(make_track(user))
        session.add(Entry(event_type=event_type, date=dt.date(2026, 11, 2)))
    session.commit()

    session.delete(owner)
    session.commit()

    assert [t.user_id for t in session.scalars(select(Track))] == [other.id]
    assert count(session, EventType) == 1
    assert count(session, Entry) == 1


def test_default_view_defaults_to_month_and_rejects_other_values(session: Session) -> None:
    user = User(username="carol", password_hash="x")
    session.add(user)
    session.commit()
    assert user.default_view == "month"

    user.default_view = "year"
    with pytest.raises(IntegrityError):
        session.commit()
