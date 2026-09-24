"""JSON file persistence.

The store owns the on-disk format, so the domain model stays persistence-agnostic.
Writes are atomic (temp file + ``os.replace``) and loads recover gracefully from a
missing or corrupt file without destroying data.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

from .model import Alarm, Repeat


def default_store_path() -> Path:
    override = os.environ.get("ALARMCLOCK_STORE")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME")
    base_path = Path(base) if base else Path.home() / ".config"
    return base_path / "alarmclock" / "alarms.json"


def to_dict(alarm: Alarm) -> dict:
    return {
        "id": alarm.id,
        "time": alarm.time.strftime("%H:%M"),
        "label": alarm.label,
        "repeat": alarm.repeat.value,
        "weekdays": sorted(alarm.weekdays),
        "enabled": alarm.enabled,
        "created_at": alarm.created_at.isoformat() if alarm.created_at else None,
    }


def from_dict(data: dict) -> Alarm:
    hh, mm = str(data["time"]).split(":")
    created = data.get("created_at")
    return Alarm(
        id=str(data["id"]),
        time=dt.time(int(hh), int(mm)),
        label=str(data.get("label", "")),
        repeat=Repeat(data.get("repeat", "daily")),
        weekdays=frozenset(int(x) for x in data.get("weekdays", [])),
        enabled=bool(data.get("enabled", True)),
        created_at=dt.datetime.fromisoformat(created) if created else None,
    )


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else default_store_path()

    def load(self) -> list[Alarm]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            backup = Path(str(self.path) + ".corrupt")
            print(
                f"warning: alarm store is unreadable ({exc}); backing up to {backup}",
                file=sys.stderr,
            )
            try:
                self.path.replace(backup)
            except OSError:
                pass
            return []

        if not isinstance(raw, list):
            print("warning: alarm store has an unexpected shape; ignoring.", file=sys.stderr)
            return []

        alarms: list[Alarm] = []
        for entry in raw:
            try:
                alarms.append(from_dict(entry))
            except (KeyError, ValueError, TypeError) as exc:
                print(f"warning: skipping invalid alarm entry ({exc}).", file=sys.stderr)
        return alarms

    def save(self, alarms: list[Alarm]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps([to_dict(a) for a in alarms], indent=2)
        tmp = Path(str(self.path) + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self.path)  # atomic
