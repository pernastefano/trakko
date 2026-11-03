import datetime as dt

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("default_view IN ('day', 'week', 'month')", name="ck_users_default_view"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    # The calendar view the app opens with for this user.
    default_view: Mapped[str] = mapped_column(String(5), default="month", server_default="month")
    # The color theme; NULL until the user (or their first device) picks one. Not constrained in
    # the database so themes can be added or retired without a migration: the API validates it.
    theme: Mapped[str | None] = mapped_column(String(16), default=None)

    tracks: Mapped[list["Track"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Track.position",
    )


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        # At most one default Track per user; "exactly one" is enforced by the service layer.
        Index(
            "uq_tracks_one_default_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("is_default = 1"),
        ),
        Index("ix_tracks_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    is_default: Mapped[bool] = mapped_column(default=False, server_default="0")

    user: Mapped[User] = relationship(back_populates="tracks")
    event_types: Mapped[list["EventType"]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="EventType.position",
    )


class EventType(Base):
    __tablename__ = "event_types"
    __table_args__ = (
        CheckConstraint("icon_kind IN ('none', 'emoji', 'text')", name="ck_event_types_icon_kind"),
        Index("ix_event_types_track_id", "track_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7))
    icon_kind: Mapped[str] = mapped_column(String(5), default="none", server_default="none")
    icon_value: Mapped[str] = mapped_column(String(16), default="", server_default="")
    position: Mapped[int] = mapped_column(default=0, server_default="0")

    track: Mapped[Track] = relationship(back_populates="event_types")
    entries: Mapped[list["Entry"]] = relationship(
        back_populates="event_type",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint("note IS NULL OR length(note) <= 280", name="ck_entries_note_length"),
        Index("ix_entries_event_type_id", "event_type_id"),
        Index("ix_entries_date", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type_id: Mapped[int] = mapped_column(ForeignKey("event_types.id", ondelete="CASCADE"))
    date: Mapped[dt.date]
    note: Mapped[str | None] = mapped_column(String(280))
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    event_type: Mapped[EventType] = relationship(back_populates="entries")
