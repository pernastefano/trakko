from fastapi import APIRouter, Request, Response

from app.deps import SessionDep, SettingsDep, session_user
from app.models import User
from app.schemas import AuthStatus, LoginRequest, RegisterRequest
from app.services import auth, users

router = APIRouter(prefix="/auth", tags=["auth"])


def _status(session: SessionDep, settings: SettingsDep, user: User | None) -> AuthStatus:
    return AuthStatus(
        authenticated=user is not None,
        username=user.username if user else None,
        registration_open=users.registration_open(session, settings),
    )


def _sign_in(request: Request, response: Response, settings: SettingsDep, user: User) -> None:
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.create_token(settings.secret_key, user.id),
        max_age=auth.SESSION_SECONDS,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )


@router.get("/status", response_model=AuthStatus)
def status(request: Request, session: SessionDep, settings: SettingsDep):
    return _status(session, settings, session_user(request, session, settings))


@router.post("/register", response_model=AuthStatus, status_code=201)
def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
):
    user = users.register(session, settings, data.username, data.password)
    _sign_in(request, response, settings, user)
    return _status(session, settings, user)


@router.post("/login", response_model=AuthStatus)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
):
    user = users.authenticate(session, data.username, data.password)
    _sign_in(request, response, settings, user)
    return _status(session, settings, user)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(auth.COOKIE_NAME)
