from fastapi import APIRouter

from app.deps import SessionDep
from app.schemas import OrderUpdate, TrackCreate, TrackRead, TrackUpdate
from app.services import tracks

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackRead])
def list_tracks(session: SessionDep):
    return tracks.list_tracks(session)


@router.post("", response_model=TrackRead, status_code=201)
def create_track(data: TrackCreate, session: SessionDep):
    return tracks.create_track(session, data)


@router.put("/order", response_model=list[TrackRead])
def reorder_tracks(data: OrderUpdate, session: SessionDep):
    return tracks.reorder_tracks(session, data.ids)


@router.get("/{track_id}", response_model=TrackRead)
def get_track(track_id: int, session: SessionDep):
    return tracks.get_track(session, track_id)


@router.patch("/{track_id}", response_model=TrackRead)
def update_track(track_id: int, data: TrackUpdate, session: SessionDep):
    return tracks.update_track(session, track_id, data)


@router.delete("/{track_id}", status_code=204)
def delete_track(track_id: int, session: SessionDep) -> None:
    tracks.delete_track(session, track_id)
