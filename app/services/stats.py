import calendar
import datetime as dt
from collections import Counter, defaultdict
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entry, EventType
from app.schemas import Bucket, EventTypeStats, HeatmapDay, Period, StatsRead
from app.services.tracks import get_track

ONE_DAY = dt.timedelta(days=1)


def period_range(period: Period, ref: dt.date) -> tuple[dt.date | None, dt.date | None]:
    if period == "month":
        last_day = calendar.monthrange(ref.year, ref.month)[1]
        return ref.replace(day=1), ref.replace(day=last_day)
    if period == "year":
        return dt.date(ref.year, 1, 1), dt.date(ref.year, 12, 31)
    return None, None


def compute_streaks(days: Sequence[dt.date], ref: dt.date) -> tuple[int, int]:
    """Return (current, longest) streaks of consecutive days.

    `days` must be sorted and distinct. The current streak counts days up to `ref` and is
    still alive when the last entry is today or yesterday.
    """
    longest = run = 0
    previous: dt.date | None = None
    current = 0
    for day in days:
        run = run + 1 if previous is not None and day - previous == ONE_DAY else 1
        longest = max(longest, run)
        if day <= ref:
            current = run if ref - day <= ONE_DAY else 0
        previous = day
    return current, longest


def average_interval(days: Sequence[dt.date]) -> float | None:
    """Mean number of days between consecutive distinct days, or None with fewer than two."""
    if len(days) < 2:
        return None
    gaps = [(later - earlier).days for earlier, later in zip(days, days[1:], strict=False)]
    return round(sum(gaps) / len(gaps), 2)


def _month_start(day: dt.date) -> dt.date:
    return day.replace(day=1)


def _next_month(day: dt.date) -> dt.date:
    return (day.replace(day=28) + dt.timedelta(days=4)).replace(day=1)


def _build_buckets(
    counts: Counter[dt.date], granularity: str, start: dt.date | None, end: dt.date | None
) -> list[Bucket]:
    if start is None or end is None:
        return []
    totals: Counter[dt.date] = Counter()
    for day, count in counts.items():
        key = day - dt.timedelta(days=day.weekday()) if granularity == "week" else _month_start(day)
        totals[key] += count
    buckets = []
    if granularity == "week":
        cursor = start - dt.timedelta(days=start.weekday())
        while cursor <= end:
            buckets.append(Bucket(start=cursor, count=totals[cursor]))
            cursor += dt.timedelta(days=7)
    else:
        cursor = _month_start(start)
        while cursor <= end:
            buckets.append(Bucket(start=cursor, count=totals[cursor]))
            cursor = _next_month(cursor)
    return buckets


def _event_type_stats(
    event_type: EventType, dates: list[dt.date], in_range: list[dt.date], ref: dt.date
) -> EventTypeStats:
    days = sorted(set(dates))
    current, longest = compute_streaks(days, ref)
    past = [day for day in days if day <= ref]
    last_date = past[-1] if past else None
    return EventTypeStats(
        event_type_id=event_type.id,
        name=event_type.name,
        color=event_type.color,
        icon_kind=event_type.icon_kind,
        icon_value=event_type.icon_value,
        count=len(in_range),
        last_date=last_date,
        days_since_last=None if last_date is None else (ref - last_date).days,
        current_streak=current,
        longest_streak=longest,
        average_interval_days=average_interval(days),
    )


def get_stats(
    session: Session,
    track_id: int,
    period: Period,
    ref: dt.date,
    today: dt.date | None = None,
) -> StatsRead:
    """Statistics for a Track.

    Counts, buckets and the heatmap are limited to the period around `ref`; streaks, days since
    the last entry and the average interval always use the whole history, with `today` (default
    `ref`) as the current day.
    """
    today = today or ref
    get_track(session, track_id)
    event_types = session.scalars(
        select(EventType)
        .where(EventType.track_id == track_id)
        .order_by(EventType.position, EventType.id)
    ).all()
    rows = session.execute(
        select(Entry.event_type_id, Entry.date)
        .join(EventType)
        .where(EventType.track_id == track_id)
    ).all()

    dates_by_type: dict[int, list[dt.date]] = defaultdict(list)
    for event_type_id, day in rows:
        dates_by_type[event_type_id].append(day)

    start, end = period_range(period, ref)
    if start is None:
        all_days = [day for _, day in rows]
        start, end = (min(all_days), max(all_days)) if all_days else (None, None)

    def within(day: dt.date) -> bool:
        return start is not None and end is not None and start <= day <= end

    stats = []
    day_counts: Counter[dt.date] = Counter()
    for event_type in event_types:
        dates = dates_by_type[event_type.id]
        in_range = [day for day in dates if within(day)]
        day_counts.update(in_range)
        stats.append(_event_type_stats(event_type, dates, in_range, today))

    granularity = "week" if period == "month" else "month"
    return StatsRead(
        track_id=track_id,
        period=period,
        start=start,
        end=end,
        granularity=granularity,
        event_types=stats,
        buckets=_build_buckets(day_counts, granularity, start, end),
        heatmap=[HeatmapDay(date=day, count=day_counts[day]) for day in sorted(day_counts)],
    )
