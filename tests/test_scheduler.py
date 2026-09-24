import datetime as dt

import pytest

from alarmclock.model import Alarm, Repeat
from alarmclock.scheduler import is_due, next_fire, occurs_on

# Reference calendar (all in 2026):
#   Jan 5 = Monday, Jan 6 = Tuesday, Jan 10 = Saturday, Jan 12 = next Monday
MON = dt.date(2026, 1, 5)
TUE = dt.date(2026, 1, 6)
SAT = dt.date(2026, 1, 10)
NEXT_MON = dt.date(2026, 1, 12)
WEEKDAYS = frozenset({0, 1, 2, 3, 4})  # Mon–Fri


def mk(hh, mm, repeat=Repeat.DAILY, weekdays=frozenset(), enabled=True):
    return Alarm(
        id="t", time=dt.time(hh, mm), repeat=repeat, weekdays=weekdays, enabled=enabled
    )


def at(day, hh, mm, ss=0):
    return dt.datetime(day.year, day.month, day.day, hh, mm, ss)


# ---- occurs_on ----
def test_daily_occurs_every_day():
    assert occurs_on(mk(7, 30, Repeat.DAILY), SAT)


def test_weekly_excludes_weekend():
    a = mk(7, 30, Repeat.WEEKLY, WEEKDAYS)
    assert occurs_on(a, MON)
    assert not occurs_on(a, SAT)


# ---- is_due ----
def test_due_at_exact_minute():
    assert is_due(mk(7, 30), at(MON, 7, 30))


def test_not_due_one_minute_later():
    assert not is_due(mk(7, 30), at(MON, 7, 31))


def test_weekly_not_due_on_excluded_day():
    a = mk(7, 30, Repeat.WEEKLY, WEEKDAYS)
    assert not is_due(a, at(SAT, 7, 30))


def test_disabled_never_due():
    assert not is_due(mk(7, 30, enabled=False), at(MON, 7, 30))


def test_due_ignores_seconds():
    assert is_due(mk(7, 30), at(MON, 7, 30, 45))


# ---- next_fire ----
@pytest.mark.parametrize(
    "alarm, now, expected",
    [
        (mk(7, 30), at(MON, 6, 0), at(MON, 7, 30)),                 # later today
        (mk(7, 30), at(MON, 8, 0), at(TUE, 7, 30)),                 # rolls to tomorrow
        (mk(7, 30), at(MON, 7, 30, 15), at(MON, 7, 30)),           # within the fire minute
        (mk(0, 0), at(MON, 23, 59), at(TUE, 0, 0)),                 # midnight wrap
        (mk(9, 0, Repeat.WEEKLY, frozenset({0})), at(TUE, 10, 0),   # weekly Mon after Tue
         at(NEXT_MON, 9, 0)),
        (mk(14, 0, Repeat.ONCE), at(MON, 15, 0), at(TUE, 14, 0)),   # once, already passed today
    ],
)
def test_next_fire(alarm, now, expected):
    assert next_fire(alarm, now) == expected


# ---- model validation ----
def test_weekly_requires_weekdays():
    with pytest.raises(ValueError):
        Alarm(id="t", time=dt.time(7, 30), repeat=Repeat.WEEKLY, weekdays=frozenset())


def test_rejects_out_of_range_weekday():
    with pytest.raises(ValueError):
        Alarm(id="t", time=dt.time(7, 30), repeat=Repeat.WEEKLY, weekdays=frozenset({7}))


def test_non_weekly_drops_weekdays():
    a = Alarm(id="t", time=dt.time(7, 30), repeat=Repeat.DAILY, weekdays=frozenset({0}))
    assert a.weekdays == frozenset()
