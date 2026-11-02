from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import InvalidError, NotFoundError
from app.models import Entry, EventType
from app.schemas import EventTypeCreate, EventTypeRead, EventTypeUpdate, check_icon
from app.services.ordering import apply_order
from app.services.tracks import get_track


def _read(event_type: EventType, entry_count: int) -> EventTypeRead:
    return EventTypeRead(
        id=event_type.id,
        track_id=event_type.track_id,
        name=event_type.name,
        color=event_type.color,
        icon_kind=event_type.icon_kind,
        icon_value=event_type.icon_value,
        position=event_type.position,
        entry_count=entry_count,
    )


def _entry_count(session: Session, event_type_id: int) -> int:
    stmt = select(func.count()).select_from(Entry).where(Entry.event_type_id == event_type_id)
    return session.scalar(stmt) or 0


def get_event_type(session: Session, event_type_id: int) -> EventType:
    event_type = session.get(EventType, event_type_id)
    if event_type is None:
        raise NotFoundError("Event type not found")
    return event_type


def _track_event_types(session: Session, track_id: int) -> list[EventType]:
    stmt = (
        select(EventType)
        .where(EventType.track_id == track_id)
        .order_by(EventType.position, EventType.id)
    )
    return list(session.scalars(stmt))


def list_event_types(session: Session, track_id: int) -> list[EventTypeRead]:
    get_track(session, track_id)
    stmt = (
        select(EventType, func.count(Entry.id))
        .outerjoin(Entry, Entry.event_type_id == EventType.id)
        .where(EventType.track_id == track_id)
        .group_by(EventType.id)
        .order_by(EventType.position, EventType.id)
    )
    return [_read(event_type, count) for event_type, count in session.execute(stmt)]


def create_event_type(session: Session, track_id: int, data: EventTypeCreate) -> EventTypeRead:
    get_track(session, track_id)
    last_position = session.scalar(
        select(func.max(EventType.position)).where(EventType.track_id == track_id)
    )
    event_type = EventType(
        track_id=track_id,
        name=data.name,
        color=data.color,
        icon_kind=data.icon_kind,
        icon_value=data.icon_value,
        position=0 if last_position is None else last_position + 1,
    )
    session.add(event_type)
    session.commit()
    return _read(event_type, 0)


def update_event_type(session: Session, event_type_id: int, data: EventTypeUpdate) -> EventTypeRead:
    event_type = get_event_type(session, event_type_id)
    if data.name is not None:
        event_type.name = data.name
    if data.color is not None:
        event_type.color = data.color
    kind = event_type.icon_kind if data.icon_kind is None else data.icon_kind
    value = event_type.icon_value if data.icon_value is None else data.icon_value
    try:
        check_icon(kind, value)
    except ValueError as error:
        raise InvalidError(str(error)) from error
    event_type.icon_kind = kind
    event_type.icon_value = value
    session.commit()
    return _read(event_type, _entry_count(session, event_type.id))


def reorder_event_types(session: Session, track_id: int, ids: list[int]) -> list[EventTypeRead]:
    get_track(session, track_id)
    apply_order(_track_event_types(session, track_id), ids, "Event type")
    session.commit()
    return list_event_types(session, track_id)


def delete_event_type(session: Session, event_type_id: int) -> None:
    session.delete(get_event_type(session, event_type_id))
    session.commit()
