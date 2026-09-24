"""Domain model — pure data, no I/O.

An Alarm is immutable; state changes (enable/disable) are done functionally with
``dataclasses.replace``. Serialization lives in the store, so the model has no idea
a file or JSON format exists.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from enum import StrEnum

WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]  # 0=Mon … 6=Sun


def new_id() -> str:
    """A short, unique-enough id for an alarm."""
    return uuid.uuid4().hex[:6]


def weekday_from_name(name: str) -> int:
    key = name.strip().lower()
    if key not in WEEKDAY_NAMES:
        raise ValueError(f"Invalid weekday {name!r}. Use one of: {', '.join(WEEKDAY_NAMES)}.")
    return WEEKDAY_NAMES.index(key)


def weekday_to_name(day: int) -> str:
    return WEEKDAY_NAMES[day]


class Repeat(StrEnum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


@dataclass(frozen=True)
class Alarm:
    id: str
    time: dt.time
    label: str = ""
    repeat: Repeat = Repeat.DAILY
    weekdays: frozenset[int] = frozenset()  # 0=Mon … 6=Sun, only for WEEKLY
    enabled: bool = True
    created_at: dt.datetime | None = None

    def __post_init__(self) -> None:
        # Coerce to a frozenset so callers can pass any iterable.
        object.__setattr__(self, "weekdays", frozenset(self.weekdays))
        if any(d < 0 or d > 6 for d in self.weekdays):
            raise ValueError("Weekdays must be integers 0..6 (Mon..Sun).")
        if self.repeat == Repeat.WEEKLY and not self.weekdays:
            raise ValueError("A weekly alarm needs at least one weekday.")
        if self.repeat != Repeat.WEEKLY and self.weekdays:
            # Non-weekly alarms don't carry weekdays.
            object.__setattr__(self, "weekdays", frozenset())
