from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.errors import UnauthorizedError
from app.services import auth

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def require_auth(request: Request, settings: SettingsDep) -> None:
    if not auth.is_authenticated(settings, request.cookies.get(auth.COOKIE_NAME)):
        raise UnauthorizedError("Authentication required")
