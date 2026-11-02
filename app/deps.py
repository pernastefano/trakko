import hmac
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
    claims = auth.parse_token(settings.secret_key, token) if token else None
    if claims is None:
        return None
    user_id, token_fingerprint = claims
    user = users.get_user(session, user_id)
    if user is None:
        return None
    current = auth.fingerprint(settings.secret_key, user.password_hash)
    # A token issued before the last password change no longer counts.
    return user if hmac.compare_digest(token_fingerprint, current) else None


def current_user(request: Request, session: SessionDep, settings: SettingsDep) -> User:
    user = session_user(request, session, settings)
    if user is None:
        raise UnauthorizedError("Authentication required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
