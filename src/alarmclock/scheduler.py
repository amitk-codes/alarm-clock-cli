"""Scheduling logic — pure functions with the clock injected as ``now``.

Nothing here calls ``datetime.now()``; callers pass the current time. That is what
makes every time-based rule deterministically testable without waiting for wall time.
"""

from __future__ import annotations

import datetime as dt

from .model import Alarm, Repeat


def occurs_on(alarm: Alarm, day: dt.date) -> bool:
    """Whether the alarm's schedule includes this calendar day."""
    if alarm.repeat == Repeat.WEEKLY:
        return day.weekday() in alarm.weekdays
    # ONCE and DAILY occur every day; single-fire for ONCE is handled by the runner.
    return True


def is_due(alarm: Alarm, now: dt.datetime) -> bool:
    """Whether the alarm should ring during this exact minute."""
    if not alarm.enabled:
        return False
    return (
        occurs_on(alarm, now.date())
        and now.hour == alarm.time.hour
        and now.minute == alarm.time.minute
    )


def next_fire(alarm: Alarm, now: dt.datetime) -> dt.datetime:
    """The next datetime at or after ``now`` (minute resolution) that the alarm fires."""
    floor = now.replace(second=0, microsecond=0)
    day = now.date()
    for _ in range(8):  # any weekly schedule recurs within 7 days
        if occurs_on(alarm, day):
            fire = dt.datetime.combine(day, alarm.time)
            if fire >= floor:
                return fire
        day += dt.timedelta(days=1)
    raise ValueError("No upcoming fire time found for alarm.")
