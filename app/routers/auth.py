from fastapi import APIRouter, Request, Response

from app.deps import SettingsDep
from app.errors import UnauthorizedError
from app.schemas import AuthStatus, LoginRequest
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=AuthStatus)
def status(request: Request, settings: SettingsDep):
    return AuthStatus(
        auth_required=auth.auth_required(settings),
        authenticated=auth.is_authenticated(settings, request.cookies.get(auth.COOKIE_NAME)),
    )


@router.post("/login", response_model=AuthStatus)
def login(data: LoginRequest, request: Request, response: Response, settings: SettingsDep):
    if not auth.check_password(settings, data.password):
        raise UnauthorizedError("Invalid password")
    if settings.password is not None and settings.secret_key is not None:
        response.set_cookie(
            auth.COOKIE_NAME,
            auth.create_token(settings.secret_key),
            max_age=auth.SESSION_SECONDS,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
    return AuthStatus(auth_required=auth.auth_required(settings), authenticated=True)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    response.delete_cookie(auth.COOKIE_NAME)
