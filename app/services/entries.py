import datetime as dt
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import InvalidError, NotFoundError
from app.models import Entry, EventType
from app.schemas import EntryCreate, EntryUpdate
from app.services.tracks import get_track


def list_entries(
    session: Session,
    *,
    track_id: int | None = None,
    event_type_id: int | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> Sequence[Entry]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidError("'from' must not be after 'to'")
    stmt = select(Entry).order_by(Entry.date, Entry.id)
    if track_id is not None:
        get_track(session, track_id)
        stmt = stmt.join(EventType).where(EventType.track_id == track_id)
    if event_type_id is not None:
        stmt = stmt.where(Entry.event_type_id == event_type_id)
    if date_from is not None:
        stmt = stmt.where(Entry.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Entry.date <= date_to)
    return session.scalars(stmt).all()


def get_entry(session: Session, entry_id: int) -> Entry:
    entry = session.get(Entry, entry_id)
    if entry is None:
        raise NotFoundError("Entry not found")
    return entry


def _get_event_type_for_body(session: Session, event_type_id: int) -> EventType:
    event_type = session.get(EventType, event_type_id)
    if event_type is None:
        raise InvalidError("event_type_id does not match any Event type")
    return event_type


def create_entry(session: Session, data: EntryCreate) -> Entry:
    _get_event_type_for_body(session, data.event_type_id)
    entry = Entry(event_type_id=data.event_type_id, date=data.date, note=data.note)
    session.add(entry)
    session.commit()
    return entry


def update_entry(session: Session, entry_id: int, data: EntryUpdate) -> Entry:
    entry = get_entry(session, entry_id)
    if data.event_type_id is not None and data.event_type_id != entry.event_type_id:
        new_type = _get_event_type_for_body(session, data.event_type_id)
        if new_type.track_id != entry.event_type.track_id:
            raise InvalidError("An entry cannot be moved to an Event type of another Track")
        entry.event_type_id = new_type.id
    if data.date is not None:
        entry.date = data.date
    if "note" in data.model_fields_set:
        entry.note = data.note
    session.commit()
    return entry


def delete_entry(session: Session, entry_id: int) -> None:
    session.delete(get_entry(session, entry_id))
    session.commit()
