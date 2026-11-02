import hashlib
import hmac
import time

COOKIE_NAME = "trakko_session"
SESSION_SECONDS = 30 * 24 * 60 * 60


def _sign(secret_key: str, payload: str) -> str:
    return hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(secret_key: str, user_id: int, now: float | None = None) -> str:
    """`<user id>.<expiry>.<signature>`; the signature covers the first two parts."""
    expires = int((time.time() if now is None else now) + SESSION_SECONDS)
    payload = f"{user_id}.{expires}"
    return f"{payload}.{_sign(secret_key, payload)}"


def verify_token(secret_key: str, token: str, now: float | None = None) -> int | None:
    """The user id the token was issued to, or None if it is forged, malformed or expired."""
    user_id, _, rest = token.partition(".")
    expires, _, signature = rest.partition(".")
    if not (user_id.isdigit() and expires.isdigit()):
        return None
    if not hmac.compare_digest(signature, _sign(secret_key, f"{user_id}.{expires}")):
        return None
    if int(expires) <= (time.time() if now is None else now):
        return None
    return int(user_id)
