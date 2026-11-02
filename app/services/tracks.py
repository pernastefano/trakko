from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.errors import ConflictError, InvalidError, NotFoundError
from app.models import Track
from app.schemas import TrackCreate, TrackUpdate
from app.services.ordering import apply_order


def list_tracks(session: Session, user_id: int) -> Sequence[Track]:
    stmt = select(Track).where(Track.user_id == user_id).order_by(Track.position, Track.id)
    return session.scalars(stmt).all()


def get_track(session: Session, user_id: int, track_id: int) -> Track:
    """A Track of this user; other users' Tracks look like they do not exist."""
    track = session.scalar(select(Track).where(Track.id == track_id, Track.user_id == user_id))
    if track is None:
        raise NotFoundError("Track not found")
    return track


def _make_default(session: Session, track: Track) -> None:
    session.execute(
        update(Track)
        .where(Track.user_id == track.user_id, Track.id != track.id)
        .values(is_default=False)
    )
    track.is_default = True


def create_track(session: Session, user_id: int, data: TrackCreate) -> Track:
    last_position = session.scalar(select(func.max(Track.position)).where(Track.user_id == user_id))
    is_first = last_position is None
    track = Track(
        user_id=user_id,
        name=data.name,
        position=0 if last_position is None else last_position + 1,
        is_default=is_first,
    )
    session.add(track)
    session.commit()
    return track


def update_track(session: Session, user_id: int, track_id: int, data: TrackUpdate) -> Track:
    track = get_track(session, user_id, track_id)
    if data.name is not None:
        track.name = data.name
    if data.is_default is True:
        _make_default(session, track)
    elif data.is_default is False and track.is_default:
        raise InvalidError("The default Track cannot be unset; set another Track as default")
    session.commit()
    return track


def reorder_tracks(session: Session, user_id: int, ids: list[int]) -> Sequence[Track]:
    apply_order(list_tracks(session, user_id), ids, "Track")
    session.commit()
    return list_tracks(session, user_id)


def delete_track(session: Session, user_id: int, track_id: int) -> None:
    track = get_track(session, user_id, track_id)
    if len(list_tracks(session, user_id)) == 1:
        raise ConflictError("The only Track cannot be deleted")
    was_default = track.is_default
    session.delete(track)
    session.flush()
    if was_default:
        _make_default(session, list_tracks(session, user_id)[0])
    session.commit()
