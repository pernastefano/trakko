import datetime as dt
import re
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
    model_validator,
)

NOTE_MAX_LENGTH = 280
ICON_VALUE_MAX_LENGTH = 16

IconKind = Literal["none", "emoji", "text"]
Period = Literal["month", "year", "all"]
CalendarView = Literal["day", "week", "month"]
# Must match THEMES in static/js/theme.js and the [data-theme] blocks in app.css (tests check it).
THEME_IDS = ("auto", "graphite", "midnight", "forest", "ember", "paper", "sand")
ThemeId = Literal["auto", "graphite", "midnight", "forest", "ember", "paper", "sand"]

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _require_iso_date(value: object) -> object:
    # Reject timestamps and other loosely-parsed inputs: dates are plain calendar dates.
    if isinstance(value, str) and _ISO_DATE.fullmatch(value):
        return value
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    raise ValueError("must be a date in YYYY-MM-DD format")


def _clean_note(value: object) -> object:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("must be a string")
    return value.strip() or None


def _check_note_length(value: str | None) -> str | None:
    if value is not None and len(value) > NOTE_MAX_LENGTH:
        raise ValueError(f"must be at most {NOTE_MAX_LENGTH} characters")
    return value


def _to_naive_utc(value: dt.datetime | None) -> dt.datetime | None:
    if value is not None and value.tzinfo is not None:
        return value.astimezone(dt.UTC).replace(tzinfo=None)
    return value


def check_icon(kind: str, value: str) -> None:
    """Raise ValueError unless (kind, value) is a valid icon."""
    if kind == "none":
        if value:
            raise ValueError("icon_value must be empty when icon_kind is 'none'")
    elif kind == "emoji":
        if not value or len(value) > ICON_VALUE_MAX_LENGTH or any(c.isalnum() for c in value):
            raise ValueError("icon_value must be an emoji or symbol when icon_kind is 'emoji'")
        if any(c.isspace() for c in value):
            raise ValueError("icon_value must not contain spaces")
    elif not (1 <= len(value) <= 2 and value.isalnum()):
        raise ValueError("icon_value must be one or two letters or digits when icon_kind is 'text'")


IsoDate = Annotated[dt.date, BeforeValidator(_require_iso_date)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Color = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$"), AfterValidator(str.lower)]
Note = Annotated[str | None, BeforeValidator(_clean_note), AfterValidator(_check_note_length)]
NaiveUtcDateTime = Annotated[dt.datetime | None, AfterValidator(_to_naive_utc)]


class Reader(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Tracks ---


class TrackCreate(BaseModel):
    name: Name


class TrackUpdate(BaseModel):
    name: Name | None = None
    is_default: bool | None = None


class TrackRead(Reader):
    id: int
    name: str
    position: int
    is_default: bool


class OrderUpdate(BaseModel):
    ids: list[int]


# --- Event types ---


class EventTypeCreate(BaseModel):
    name: Name
    color: Color
    icon_kind: IconKind = "none"
    icon_value: str = ""

    @model_validator(mode="after")
    def validate_icon(self) -> "EventTypeCreate":
        check_icon(self.icon_kind, self.icon_value)
        return self


class EventTypeUpdate(BaseModel):
    name: Name | None = None
    color: Color | None = None
    icon_kind: IconKind | None = None
    icon_value: str | None = None


class EventTypeRead(Reader):
    id: int
    track_id: int
    name: str
    color: str
    icon_kind: IconKind
    icon_value: str
    position: int
    entry_count: int


# --- Entries ---


class EntryCreate(BaseModel):
    event_type_id: int
    date: IsoDate
    note: Note = None


class EntryUpdate(BaseModel):
    event_type_id: int | None = None
    date: IsoDate | None = None
    note: Note = None


class EntryRead(Reader):
    id: int
    event_type_id: int
    date: dt.date
    note: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, value: dt.datetime) -> str:
        # Timestamps are stored as naive UTC; make the zone explicit for clients.
        return value.isoformat() + "Z"


# --- Statistics ---


class EventTypeStats(BaseModel):
    event_type_id: int
    name: str
    color: str
    icon_kind: IconKind
    icon_value: str
    count: int
    last_date: dt.date | None
    days_since_last: int | None
    current_streak: int
    longest_streak: int
    average_interval_days: float | None


class Bucket(BaseModel):
    start: dt.date
    count: int


class HeatmapDay(BaseModel):
    date: dt.date
    count: int


class StatsRead(BaseModel):
    track_id: int
    period: Period
    start: dt.date | None
    end: dt.date | None
    granularity: Literal["week", "month"]
    event_types: list[EventTypeStats]
    buckets: list[Bucket]
    heatmap: list[HeatmapDay]


# --- Export / import ---


class DataEntry(BaseModel):
    date: IsoDate
    note: Note = None
    created_at: NaiveUtcDateTime = None
    updated_at: NaiveUtcDateTime = None

    @field_serializer("created_at", "updated_at")
    def serialize_timestamp(self, value: dt.datetime | None) -> str | None:
        # Timestamps are stored as naive UTC; make the zone explicit in the file.
        return None if value is None else value.isoformat() + "Z"


class DataEventType(BaseModel):
    name: Name
    color: Color
    icon_kind: IconKind = "none"
    icon_value: str = ""
    entries: list[DataEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_icon(self) -> "DataEventType":
        check_icon(self.icon_kind, self.icon_value)
        return self


class DataTrack(BaseModel):
    name: Name
    is_default: bool = False
    event_types: list[DataEventType] = Field(default_factory=list)


class DataFile(BaseModel):
    version: Literal[1] = 1
    exported_at: dt.datetime | None = None
    tracks: list[DataTrack]

    @model_validator(mode="after")
    def validate_tracks(self) -> "DataFile":
        if not self.tracks:
            raise ValueError("tracks must contain at least one Track")
        if sum(track.is_default for track in self.tracks) != 1:
            raise ValueError("exactly one Track must be the default")
        return self


# --- Accounts ---


USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")


def _normalize_username(value: object) -> object:
    # Names are case-insensitive: store them lowercase.
    return value.strip().lower() if isinstance(value, str) else value


def _check_username(value: str) -> str:
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError(
            "must be 3 to 32 characters: letters, digits, dots, dashes or underscores, "
            "starting with a letter or digit"
        )
    return value


Username = Annotated[str, BeforeValidator(_normalize_username), AfterValidator(_check_username)]


def _check_new_password(value: str) -> str:
    if not 8 <= len(value) <= 128:
        raise ValueError("must be 8 to 128 characters")
    return value


NewPassword = Annotated[str, AfterValidator(_check_new_password)]


class RegisterRequest(BaseModel):
    username: Username
    password: NewPassword


class LoginRequest(BaseModel):
    # Loose limits: a wrong login is answered with the same message whatever the input.
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class ChangePasswordRequest(BaseModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    new_password: NewPassword


class PreferencesRead(BaseModel):
    default_view: CalendarView
    theme: ThemeId | None

    @field_validator("theme", mode="before")
    @classmethod
    def retired_theme_becomes_automatic(cls, value: object) -> object:
        # A theme that was stored and later removed must not break the settings page.
        return value if value is None or value in THEME_IDS else "auto"


class PreferencesUpdate(BaseModel):
    default_view: CalendarView | None = None
    theme: ThemeId | None = None


class AboutRead(BaseModel):
    name: str
    version: str


class AuthStatus(BaseModel):
    authenticated: bool
    username: str | None = None
    registration_open: bool
