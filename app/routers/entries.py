from typing import Annotated

from fastapi import APIRouter, Query

from app.deps import CurrentUser, SessionDep
from app.schemas import EntryCreate, EntryRead, EntryUpdate, IsoDate
from app.services import entries

router = APIRouter(prefix="/entries", tags=["entries"])


@router.get("", response_model=list[EntryRead])
def list_entries(
    session: SessionDep,
    user: CurrentUser,
    track_id: int | None = None,
    event_type_id: int | None = None,
    date_from: Annotated[IsoDate | None, Query(alias="from")] = None,
    date_to: Annotated[IsoDate | None, Query(alias="to")] = None,
):
    return entries.list_entries(
        session,
        user.id,
        track_id=track_id,
        event_type_id=event_type_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("", response_model=EntryRead, status_code=201)
def create_entry(data: EntryCreate, session: SessionDep, user: CurrentUser):
    return entries.create_entry(session, user.id, data)


@router.get("/{entry_id}", response_model=EntryRead)
def get_entry(entry_id: int, session: SessionDep, user: CurrentUser):
    return entries.get_entry(session, user.id, entry_id)


@router.patch("/{entry_id}", response_model=EntryRead)
def update_entry(entry_id: int, data: EntryUpdate, session: SessionDep, user: CurrentUser):
    return entries.update_entry(session, user.id, entry_id, data)


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: int, session: SessionDep, user: CurrentUser) -> None:
    entries.delete_entry(session, user.id, entry_id)
