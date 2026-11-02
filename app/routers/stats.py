import datetime as dt

from fastapi import APIRouter

from app.deps import SessionDep
from app.schemas import IsoDate, Period, StatsRead
from app.services import stats

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("", response_model=StatsRead)
def get_stats(
    track_id: int,
    session: SessionDep,
    period: Period = "month",
    ref: IsoDate | None = None,
    today: IsoDate | None = None,
):
    ref = ref or today or dt.date.today()
    return stats.get_stats(session, track_id, period, ref, today)
