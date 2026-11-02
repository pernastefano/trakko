from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.schemas import OrderUpdate, TrackCreate, TrackRead, TrackUpdate
from app.services import tracks

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackRead])
def list_tracks(session: SessionDep, user: CurrentUser):
    return tracks.list_tracks(session, user.id)


@router.post("", response_model=TrackRead, status_code=201)
def create_track(data: TrackCreate, session: SessionDep, user: CurrentUser):
    return tracks.create_track(session, user.id, data)


@router.put("/order", response_model=list[TrackRead])
def reorder_tracks(data: OrderUpdate, session: SessionDep, user: CurrentUser):
    return tracks.reorder_tracks(session, user.id, data.ids)


@router.get("/{track_id}", response_model=TrackRead)
def get_track(track_id: int, session: SessionDep, user: CurrentUser):
    return tracks.get_track(session, user.id, track_id)


@router.patch("/{track_id}", response_model=TrackRead)
def update_track(track_id: int, data: TrackUpdate, session: SessionDep, user: CurrentUser):
    return tracks.update_track(session, user.id, track_id, data)


@router.delete("/{track_id}", status_code=204)
def delete_track(track_id: int, session: SessionDep, user: CurrentUser) -> None:
    tracks.delete_track(session, user.id, track_id)
