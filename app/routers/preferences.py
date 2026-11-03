from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.schemas import PreferencesRead, PreferencesUpdate
from app.services import users

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PreferencesRead)
def get_preferences(user: CurrentUser):
    return user


@router.patch("", response_model=PreferencesRead)
def update_preferences(data: PreferencesUpdate, session: SessionDep, user: CurrentUser):
    return users.update_preferences(session, user, data.default_view, data.theme)
