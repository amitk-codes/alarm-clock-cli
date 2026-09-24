import datetime as dt

from alarmclock.model import Alarm, Repeat
from alarmclock.runner import Runner
from alarmclock.store import Store


class FakeClock:
    def __init__(self, start: dt.datetime) -> None:
        self.t = start

    def now(self) -> dt.datetime:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += dt.timedelta(seconds=seconds)


class FakeRinger:
    def __init__(self) -> None:
        self.rung: list[Alarm] = []

    def start(self, alarm: Alarm) -> None:
        self.rung.append(alarm)

    def stop(self) -> None:
        pass


def daily(hh, mm, *, enabled=True, alarm_id="a1"):
    return Alarm(id=alarm_id, time=dt.time(hh, mm), repeat=Repeat.DAILY, enabled=enabled)


def build(tmp_path, alarms, *, start, inputs, tick=60, snooze=9):
    store = Store(tmp_path / "a.json")
    store.save(alarms)
    clock = FakeClock(start)
    ringer = FakeRinger()
    responses = iter(inputs)
    runner = Runner(
        store,
        ringer=ringer,
        now_fn=clock.now,
        sleep_fn=clock.sleep,
        input_fn=lambda _prompt: next(responses),
        output=lambda _msg: None,
        snooze_minutes=snooze,
        tick_seconds=tick,
    )
    return runner, ringer, store


def test_fires_at_due_time(tmp_path):
    runner, ringer, _ = build(
        tmp_path, [daily(7, 31)], start=dt.datetime(2026, 1, 5, 7, 30), inputs=["d"]
    )
    runner.run(max_ticks=3)
    assert len(ringer.rung) == 1


def test_disabled_never_rings(tmp_path):
    runner, ringer, _ = build(
        tmp_path, [daily(7, 31, enabled=False)],
        start=dt.datetime(2026, 1, 5, 7, 30), inputs=["d"],
    )
    runner.run(max_ticks=3)
    assert ringer.rung == []


def test_snooze_refires(tmp_path):
    runner, ringer, _ = build(
        tmp_path, [daily(7, 31)], start=dt.datetime(2026, 1, 5, 7, 30),
        inputs=["s", "d"], snooze=2,
    )
    runner.run(max_ticks=6)
    assert len(ringer.rung) == 2


def test_once_removed_after_dismiss(tmp_path):
    once = Alarm(id="o1", time=dt.time(7, 31), repeat=Repeat.ONCE)
    runner, _ringer, store = build(
        tmp_path, [once], start=dt.datetime(2026, 1, 5, 7, 30), inputs=["d"]
    )
    runner.run(max_ticks=3)
    assert store.load() == []


def test_no_double_ring_within_minute(tmp_path):
    runner, ringer, _ = build(
        tmp_path, [daily(7, 30)], start=dt.datetime(2026, 1, 5, 7, 29, 58),
        inputs=["d"], tick=1,
    )
    runner.run(max_ticks=6)
    assert len(ringer.rung) == 1


def test_keyboard_interrupt_stops_cleanly(tmp_path):
    outputs: list[str] = []
    store = Store(tmp_path / "a.json")
    store.save([daily(7, 30)])
    clock = FakeClock(dt.datetime(2026, 1, 5, 7, 30))

    def boom(_prompt):
        raise KeyboardInterrupt

    runner = Runner(
        store, ringer=FakeRinger(), now_fn=clock.now, sleep_fn=clock.sleep,
        input_fn=boom, output=outputs.append, tick_seconds=60,
    )
    runner.run(max_ticks=3)  # must not raise
    assert any("Stopped" in o for o in outputs)
