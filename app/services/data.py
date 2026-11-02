import datetime as dt

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models import Entry, EventType, Track
from app.schemas import DataEntry, DataEventType, DataFile, DataTrack


def export_data(session: Session, user_id: int) -> DataFile:
    tracks = session.scalars(
        select(Track)
        .where(Track.user_id == user_id)
        .options(selectinload(Track.event_types).selectinload(EventType.entries))
        .order_by(Track.position, Track.id)
    ).all()
    return DataFile(
        exported_at=dt.datetime.now(dt.UTC).replace(microsecond=0),
        tracks=[
            DataTrack(
                name=track.name,
                is_default=track.is_default,
                event_types=[
                    DataEventType(
                        name=event_type.name,
                        color=event_type.color,
                        icon_kind=event_type.icon_kind,
                        icon_value=event_type.icon_value,
                        entries=[
                            DataEntry(
                                date=entry.date,
                                note=entry.note,
                                created_at=entry.created_at,
                                updated_at=entry.updated_at,
                            )
                            for entry in sorted(event_type.entries, key=lambda e: (e.date, e.id))
                        ],
                    )
                    for event_type in track.event_types
                ],
            )
            for track in tracks
        ],
    )


def _entry_from_data(data: DataEntry) -> Entry:
    entry = Entry(date=data.date, note=data.note)
    if data.created_at is not None:
        entry.created_at = data.created_at
    if data.updated_at is not None:
        entry.updated_at = data.updated_at
    return entry


def import_data(session: Session, user_id: int, data: DataFile) -> None:
    """Replace all of this user's data with the content of `data`, atomically."""
    try:
        session.execute(delete(Track).where(Track.user_id == user_id))
        for track_position, track_data in enumerate(data.tracks):
            track = Track(
                user_id=user_id,
                name=track_data.name,
                position=track_position,
                is_default=track_data.is_default,
            )
            for type_position, type_data in enumerate(track_data.event_types):
                track.event_types.append(
                    EventType(
                        name=type_data.name,
                        color=type_data.color,
                        icon_kind=type_data.icon_kind,
                        icon_value=type_data.icon_value,
                        position=type_position,
                        entries=[_entry_from_data(entry) for entry in type_data.entries],
                    )
                )
            session.add(track)
        session.commit()
    except Exception:
        session.rollback()
        raise
