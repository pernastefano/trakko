from fastapi import APIRouter

from app.deps import SessionDep
from app.schemas import DataFile
from app.services import data

router = APIRouter(tags=["data"])


@router.get("/export", response_model=DataFile)
def export_data(session: SessionDep):
    return data.export_data(session)


@router.post("/import", status_code=204)
def import_data(payload: DataFile, session: SessionDep) -> None:
    data.import_data(session, payload)
