from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.errors import UnauthorizedError
from app.models import User
from app.services import auth, users

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def session_user(request: Request, session: Session, settings: Settings) -> User | None:
    """The signed-in user for this request, or None."""
    token = request.cookies.get(auth.COOKIE_NAME)
    user_id = auth.verify_token(settings.secret_key, token) if token else None
    return users.get_user(session, user_id) if user_id is not None else None


def current_user(request: Request, session: SessionDep, settings: SettingsDep) -> User:
    user = session_user(request, session, settings)
    if user is None:
        raise UnauthorizedError("Authentication required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
