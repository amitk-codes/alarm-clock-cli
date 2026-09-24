"""The foreground scheduler loop.

Every time- and I/O-dependent collaborator is injected (clock, sleep, ringer, input),
so the whole loop runs instantly and deterministically under test.
"""

from __future__ import annotations

import datetime as dt
import time as _time
from collections.abc import Callable

from .model import Alarm, Repeat
from .ringer import ConsoleRinger, Ringer
from .scheduler import is_due
from .store import Store

MinuteKey = tuple[int, int, int, int, int]


def _minute_key(now: dt.datetime) -> MinuteKey:
    return (now.year, now.month, now.day, now.hour, now.minute)


class Runner:
    def __init__(
        self,
        store: Store,
        *,
        ringer: Ringer | None = None,
        now_fn: Callable[[], dt.datetime] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
        input_fn: Callable[[str], str] = input,
        output: Callable[[str], None] = print,
        snooze_minutes: int = 9,
        tick_seconds: float = 1.0,
    ) -> None:
        self.store = store
        self.ringer = ringer or ConsoleRinger()
        self.now_fn = now_fn or dt.datetime.now
        self.sleep_fn = sleep_fn or _time.sleep
        self.input_fn = input_fn
        self.output = output
        self.snooze_minutes = snooze_minutes
        self.tick_seconds = tick_seconds
        self._last_fired: dict[str, MinuteKey] = {}
        self._snoozed: dict[str, dt.datetime] = {}

    def run(self, max_ticks: int | None = None) -> None:
        ticks = 0
        try:
            while max_ticks is None or ticks < max_ticks:
                self._tick(self.now_fn())
                self.sleep_fn(self.tick_seconds)
                ticks += 1
        except KeyboardInterrupt:
            self.output("\nStopped.")

    def _tick(self, now: dt.datetime) -> None:
        alarms = {a.id: a for a in self.store.load()}

        # Snoozed alarms whose wake time has arrived.
        for alarm_id, wake in list(self._snoozed.items()):
            if now >= wake:
                del self._snoozed[alarm_id]
                if alarm_id in alarms:
                    self._fire(alarms[alarm_id], now)

        # Scheduled alarms due this minute (fired once per occurrence).
        for alarm in alarms.values():
            if is_due(alarm, now) and self._last_fired.get(alarm.id) != _minute_key(now):
                self._fire(alarm, now)

    def _fire(self, alarm: Alarm, now: dt.datetime) -> None:
        self._last_fired[alarm.id] = _minute_key(now)
        self.ringer.start(alarm)
        try:
            response = self.input_fn(f"[s]nooze {self.snooze_minutes}m / [d]ismiss: ")
        finally:
            self.ringer.stop()

        if response.strip().lower().startswith("s"):
            wake = now + dt.timedelta(minutes=self.snooze_minutes)
            self._snoozed[alarm.id] = wake
            self.output(f"Snoozed until {wake:%H:%M}.")
        else:
            self.output(f"Dismissed alarm {alarm.id}.")
            if alarm.repeat == Repeat.ONCE:
                self.store.save([a for a in self.store.load() if a.id != alarm.id])
