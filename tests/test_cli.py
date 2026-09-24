import datetime as dt

import pytest

from alarmclock.cli import main
from alarmclock.model import Repeat
from alarmclock.store import Store


def store_at(tmp_path):
    return Store(tmp_path / "alarms.json")


def test_add_daily(tmp_path):
    s = store_at(tmp_path)
    assert main(["add", "07:30", "--label", "Wake"], store=s) == 0
    (a,) = s.load()
    assert a.time == dt.time(7, 30)
    assert a.repeat == Repeat.DAILY
    assert a.label == "Wake"
    assert a.enabled


def test_add_once(tmp_path):
    s = store_at(tmp_path)
    main(["add", "14:00", "--repeat", "once"], store=s)
    assert s.load()[0].repeat == Repeat.ONCE


def test_add_weekly(tmp_path):
    s = store_at(tmp_path)
    main(["add", "08:00", "--repeat", "mon,fri"], store=s)
    a = s.load()[0]
    assert a.repeat == Repeat.WEEKLY
    assert a.weekdays == frozenset({0, 4})


def test_add_invalid_time(tmp_path):
    with pytest.raises(SystemExit):
        main(["add", "25:00"], store=store_at(tmp_path))


def test_add_invalid_weekday(tmp_path):
    with pytest.raises(SystemExit):
        main(["add", "08:00", "--repeat", "xyz"], store=store_at(tmp_path))


def test_list_shows_id(tmp_path, capsys):
    s = store_at(tmp_path)
    main(["add", "07:30", "--label", "Wake"], store=s)
    capsys.readouterr()
    main(["list"], store=s)
    assert s.load()[0].id in capsys.readouterr().out


def test_list_empty(tmp_path, capsys):
    main(["list"], store=store_at(tmp_path))
    assert "No alarms" in capsys.readouterr().out


def test_remove(tmp_path):
    s = store_at(tmp_path)
    main(["add", "07:30"], store=s)
    aid = s.load()[0].id
    assert main(["remove", aid], store=s) == 0
    assert s.load() == []


def test_remove_missing(tmp_path, capsys):
    assert main(["remove", "nope"], store=store_at(tmp_path)) == 1
    assert "no alarm" in capsys.readouterr().err.lower()


def test_disable_then_enable(tmp_path):
    s = store_at(tmp_path)
    main(["add", "07:30"], store=s)
    aid = s.load()[0].id
    main(["disable", aid], store=s)
    assert s.load()[0].enabled is False
    main(["enable", aid], store=s)
    assert s.load()[0].enabled is True


def test_disable_missing(tmp_path):
    assert main(["disable", "nope"], store=store_at(tmp_path)) == 1
