from fastapi import APIRouter

from app import __version__
from app.schemas import AboutRead

router = APIRouter(prefix="/about", tags=["about"])


@router.get("", response_model=AboutRead)
def get_about():
    # Like the rest of the API it needs a signed-in user; Settings shows it.
    return AboutRead(name="TRAKKO", version=__version__)
