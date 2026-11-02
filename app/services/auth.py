import hashlib
import hmac
import time

COOKIE_NAME = "trakko_session"
SESSION_SECONDS = 30 * 24 * 60 * 60
FINGERPRINT_LENGTH = 16


def _sign(secret_key: str, payload: str) -> str:
    return hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def fingerprint(secret_key: str, password_hash: str) -> str:
    """A short value that changes whenever the password does (it reveals nothing about it)."""
    return _sign(secret_key, f"password:{password_hash}")[:FINGERPRINT_LENGTH]


def create_token(
    secret_key: str, user_id: int, password_hash: str, now: float | None = None
) -> str:
    """`<user id>.<expiry>.<password fingerprint>.<signature>`; the signature covers the rest.

    Tying the token to the password means changing the password ends every other session.
    """
    expires = int((time.time() if now is None else now) + SESSION_SECONDS)
    payload = f"{user_id}.{expires}.{fingerprint(secret_key, password_hash)}"
    return f"{payload}.{_sign(secret_key, payload)}"


def parse_token(secret_key: str, token: str, now: float | None = None) -> tuple[int, str] | None:
    """`(user id, fingerprint)` of a genuine, unexpired token, or None.

    The caller must still compare the fingerprint with the user's current password.
    """
    parts = token.split(".")
    if len(parts) != 4:
        return None
    user_id, expires, token_fingerprint, signature = parts
    if not (user_id.isdigit() and expires.isdigit()):
        return None
    payload = f"{user_id}.{expires}.{token_fingerprint}"
    if not hmac.compare_digest(signature, _sign(secret_key, payload)):
        return None
    if int(expires) <= (time.time() if now is None else now):
        return None
    return int(user_id), token_fingerprint
