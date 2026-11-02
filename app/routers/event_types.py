from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.schemas import EventTypeCreate, EventTypeRead, EventTypeUpdate, OrderUpdate
from app.services import event_types

router = APIRouter(tags=["event types"])


@router.get("/tracks/{track_id}/event-types", response_model=list[EventTypeRead])
def list_event_types(track_id: int, session: SessionDep, user: CurrentUser):
    return event_types.list_event_types(session, user.id, track_id)


@router.post("/tracks/{track_id}/event-types", response_model=EventTypeRead, status_code=201)
def create_event_type(track_id: int, data: EventTypeCreate, session: SessionDep, user: CurrentUser):
    return event_types.create_event_type(session, user.id, track_id, data)


@router.put("/tracks/{track_id}/event-types/order", response_model=list[EventTypeRead])
def reorder_event_types(track_id: int, data: OrderUpdate, session: SessionDep, user: CurrentUser):
    return event_types.reorder_event_types(session, user.id, track_id, data.ids)


@router.patch("/event-types/{event_type_id}", response_model=EventTypeRead)
def update_event_type(
    event_type_id: int, data: EventTypeUpdate, session: SessionDep, user: CurrentUser
):
    return event_types.update_event_type(session, user.id, event_type_id, data)


@router.delete("/event-types/{event_type_id}", status_code=204)
def delete_event_type(event_type_id: int, session: SessionDep, user: CurrentUser) -> None:
    event_types.delete_event_type(session, user.id, event_type_id)
