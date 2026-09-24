import datetime as dt
import json

from alarmclock.model import Alarm, Repeat
from alarmclock.store import Store, default_store_path, to_dict


def sample() -> list[Alarm]:
    return [
        Alarm(id="a1", time=dt.time(7, 30), label="Wake", repeat=Repeat.DAILY,
              created_at=dt.datetime(2026, 1, 1, 9, 0, 0)),
        Alarm(id="a2", time=dt.time(8, 0), repeat=Repeat.WEEKLY,
              weekdays=frozenset({0, 1, 2, 3, 4})),
        Alarm(id="a3", time=dt.time(14, 0), repeat=Repeat.ONCE, enabled=False),
    ]


def test_round_trip(tmp_path):
    store = Store(tmp_path / "alarms.json")
    alarms = sample()
    store.save(alarms)
    assert store.load() == alarms


def test_missing_file_returns_empty(tmp_path):
    assert Store(tmp_path / "nope.json").load() == []


def test_save_creates_parent_dir(tmp_path):
    p = tmp_path / "nested" / "dir" / "alarms.json"
    Store(p).save(sample())
    assert p.exists()


def test_no_leftover_temp_file(tmp_path):
    p = tmp_path / "alarms.json"
    Store(p).save(sample())
    assert not (tmp_path / "alarms.json.tmp").exists()
    json.loads(p.read_text())  # valid JSON


def test_corrupt_file_recovers_and_backs_up(tmp_path, capsys):
    p = tmp_path / "alarms.json"
    p.write_text("{ not valid json")
    assert Store(p).load() == []
    assert (tmp_path / "alarms.json.corrupt").exists()
    assert "warning" in capsys.readouterr().err.lower()


def test_skips_invalid_entry(tmp_path, capsys):
    p = tmp_path / "alarms.json"
    p.write_text(json.dumps([to_dict(sample()[0]), {"id": "bad"}]))  # 2nd has no time
    loaded = Store(p).load()
    assert len(loaded) == 1 and loaded[0].id == "a1"
    assert "skipping" in capsys.readouterr().err.lower()


def test_serialization_details():
    a = Alarm(id="x", time=dt.time(7, 5), repeat=Repeat.WEEKLY, weekdays=frozenset({4, 0, 2}))
    d = to_dict(a)
    assert d["time"] == "07:05"
    assert d["weekdays"] == [0, 2, 4]  # sorted


def test_env_override(monkeypatch, tmp_path):
    target = tmp_path / "custom.json"
    monkeypatch.setenv("ALARMCLOCK_STORE", str(target))
    assert default_store_path() == target


def test_xdg_path(monkeypatch, tmp_path):
    monkeypatch.delenv("ALARMCLOCK_STORE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_store_path() == tmp_path / "alarmclock" / "alarms.json"
