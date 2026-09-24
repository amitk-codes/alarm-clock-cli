"""Command-line interface: argparse subcommands over the JSON store.

Input is validated at the argparse boundary (``type=`` functions), so bad arguments
fail with a clean usage error. The store is injectable so commands are unit-testable.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import sys

from . import __version__
from .model import Alarm, Repeat, new_id, weekday_from_name, weekday_to_name
from .scheduler import next_fire
from .store import Store


# ---- argument parsing / validation ----
def parse_hhmm(value: str) -> dt.time:
    try:
        hh, mm = value.split(":")
        return dt.time(int(hh), int(mm))
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError(
            f"invalid time {value!r}; expected HH:MM (24-hour)."
        ) from None


def parse_repeat(value: str) -> tuple[Repeat, frozenset[int]]:
    key = value.strip().lower()
    if key == "once":
        return (Repeat.ONCE, frozenset())
    if key == "daily":
        return (Repeat.DAILY, frozenset())
    try:
        days = frozenset(weekday_from_name(x) for x in key.split(",") if x)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not days:
        raise argparse.ArgumentTypeError("empty --repeat; use once, daily, or e.g. mon,tue,fri.")
    return (Repeat.WEEKLY, days)


# ---- display helpers ----
def describe_repeat(alarm: Alarm) -> str:
    if alarm.repeat == Repeat.WEEKLY:
        return ",".join(weekday_to_name(d).capitalize() for d in sorted(alarm.weekdays))
    return alarm.repeat.value


def _fmt_next(alarm: Alarm, now: dt.datetime) -> str:
    if not alarm.enabled:
        return "-"
    nxt = next_fire(alarm, now)
    if nxt.date() == now.date():
        return f"today {nxt:%H:%M}"
    if nxt.date() == now.date() + dt.timedelta(days=1):
        return f"tomorrow {nxt:%H:%M}"
    return f"{nxt:%a %H:%M}"


def _find(alarms: list[Alarm], alarm_id: str) -> Alarm | None:
    return next((a for a in alarms if a.id == alarm_id), None)


# ---- commands ----
def cmd_add(args: argparse.Namespace, store: Store) -> int:
    repeat, weekdays = args.repeat
    alarm = Alarm(
        id=new_id(),
        time=args.time,
        label=args.label,
        repeat=repeat,
        weekdays=weekdays,
        created_at=dt.datetime.now(),
    )
    alarms = store.load()
    alarms.append(alarm)
    store.save(alarms)
    suffix = f" — {alarm.label}" if alarm.label else ""
    print(f"Added alarm {alarm.id}: {alarm.time:%H:%M} ({describe_repeat(alarm)}){suffix}")
    return 0


def cmd_list(args: argparse.Namespace, store: Store) -> int:
    alarms = store.load()
    if not alarms:
        print('No alarms. Add one with:  alarm add 07:30 --label "Wake up"')
        return 0
    now = dt.datetime.now()
    print(f"{'ID':<8}{'TIME':<7}{'REPEAT':<14}{'ON':<5}{'NEXT':<16}LABEL")
    for a in alarms:
        print(
            f"{a.id:<8}{a.time:%H:%M}  {describe_repeat(a):<14}"
            f"{('yes' if a.enabled else 'no'):<5}{_fmt_next(a, now):<16}{a.label}"
        )
    return 0


def cmd_remove(args: argparse.Namespace, store: Store) -> int:
    alarms = store.load()
    remaining = [a for a in alarms if a.id != args.id]
    if len(remaining) == len(alarms):
        print(f"error: no alarm with id {args.id!r}.", file=sys.stderr)
        return 1
    store.save(remaining)
    print(f"Removed alarm {args.id}.")
    return 0


def _set_enabled(args: argparse.Namespace, store: Store, enabled: bool) -> int:
    alarms = store.load()
    if _find(alarms, args.id) is None:
        print(f"error: no alarm with id {args.id!r}.", file=sys.stderr)
        return 1
    updated = [
        dataclasses.replace(a, enabled=enabled) if a.id == args.id else a for a in alarms
    ]
    store.save(updated)
    print(f"{'Enabled' if enabled else 'Disabled'} alarm {args.id}.")
    return 0


def cmd_enable(args: argparse.Namespace, store: Store) -> int:
    return _set_enabled(args, store, True)


def cmd_disable(args: argparse.Namespace, store: Store) -> int:
    return _set_enabled(args, store, False)


# ---- parser + entry point ----
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="alarm", description="A command-line alarm clock.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add", help="Add an alarm")
    p_add.add_argument("time", type=parse_hhmm, metavar="HH:MM", help="24-hour time, e.g. 07:30")
    p_add.add_argument("--label", default="", help="Optional label")
    p_add.add_argument(
        "--repeat",
        type=parse_repeat,
        default=(Repeat.DAILY, frozenset()),
        metavar="once|daily|mon,tue,...",
        help="Schedule (default: daily)",
    )
    p_add.set_defaults(func=cmd_add)

    sub.add_parser("list", help="List alarms").set_defaults(func=cmd_list)

    p_rm = sub.add_parser("remove", help="Remove an alarm by id")
    p_rm.add_argument("id")
    p_rm.set_defaults(func=cmd_remove)

    p_en = sub.add_parser("enable", help="Enable an alarm by id")
    p_en.add_argument("id")
    p_en.set_defaults(func=cmd_enable)

    p_dis = sub.add_parser("disable", help="Disable an alarm by id")
    p_dis.add_argument("id")
    p_dis.set_defaults(func=cmd_disable)

    return parser


def main(argv: list[str] | None = None, store: Store | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    store = store or Store()
    return args.func(args, store)
