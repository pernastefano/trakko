import base64
import hashlib
import hmac
import secrets

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import ConflictError, ForbiddenError, UnauthorizedError
from app.models import Track, User

DEFAULT_TRACK_NAME = "My Track"

# scrypt cost (about 50 ms and 16 MiB per hash). The parameters are stored with each hash, so they
# can change later without invalidating existing passwords.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(
        password.encode(), salt=salt, n=n, r=r, p=p, dklen=KEY_BYTES, maxmem=128 * n * r * 2
    )


def hash_password(password: str) -> str:
    """`scrypt$n$r$p$salt$key`, with the salt and key base64-encoded."""
    salt = secrets.token_bytes(SALT_BYTES)
    key = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, key = stored.split("$")
        if scheme != "scrypt":
            return False
        derived = _derive(password, base64.b64decode(salt), int(n), int(r), int(p))
        return hmac.compare_digest(derived, base64.b64decode(key))
    except (ValueError, TypeError):
        return False


# Used to spend the same time on unknown usernames as on wrong passwords.
_UNKNOWN_USER_HASH = hash_password(secrets.token_urlsafe(16))


def user_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(User)) or 0


def registration_open(session: Session, settings: Settings) -> bool:
    """Registration can be switched off, but never while there is no account at all."""
    return settings.allow_registration or user_count(session) == 0


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def create_user(
    session: Session, username: str, password: str, *, with_default_track: bool = True
) -> User:
    user = User(username=username, password_hash=hash_password(password))
    if with_default_track:
        user.tracks.append(Track(name=DEFAULT_TRACK_NAME, position=0, is_default=True))
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ConflictError("That username is already taken") from error
    return user


def register(session: Session, settings: Settings, username: str, password: str) -> User:
    if not registration_open(session, settings):
        raise ForbiddenError("Registration is closed")
    return create_user(session, username, password)


def authenticate_or_none(session: Session, username: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.username == username.strip().lower()))
    # Hash even for unknown names so both failures take about the same time.
    valid = verify_password(password, user.password_hash if user else _UNKNOWN_USER_HASH)
    return user if user is not None and valid else None


def authenticate(session: Session, username: str, password: str) -> User:
    user = authenticate_or_none(session, username, password)
    if user is None:
        raise UnauthorizedError("Invalid username or password")
    return user
