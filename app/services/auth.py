import hashlib
import hmac
import time

from app.config import Settings

COOKIE_NAME = "trakko_session"
SESSION_SECONDS = 30 * 24 * 60 * 60


def auth_required(settings: Settings) -> bool:
    return settings.password is not None


def check_password(settings: Settings, candidate: str) -> bool:
    if settings.password is None:
        return True
    return hmac.compare_digest(candidate.encode(), settings.password.encode())


def _sign(secret_key: str, payload: str) -> str:
    return hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(secret_key: str, now: float | None = None) -> str:
    expires = int((time.time() if now is None else now) + SESSION_SECONDS)
    return f"{expires}.{_sign(secret_key, str(expires))}"


def verify_token(secret_key: str, token: str, now: float | None = None) -> bool:
    expires, _, signature = token.partition(".")
    if not expires.isdigit() or not hmac.compare_digest(signature, _sign(secret_key, expires)):
        return False
    return int(expires) > (time.time() if now is None else now)


def is_authenticated(settings: Settings, token: str | None) -> bool:
    if not auth_required(settings):
        return True
    if token is None or settings.secret_key is None:
        return False
    return verify_token(settings.secret_key, token)
