from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.schemas import DataFile
from app.services import data

router = APIRouter(tags=["data"])


@router.get("/export", response_model=DataFile)
def export_data(session: SessionDep, user: CurrentUser):
    return data.export_data(session, user.id)


@router.post("/import", status_code=204)
def import_data(payload: DataFile, session: SessionDep, user: CurrentUser) -> None:
    data.import_data(session, user.id, payload)
