# Alarm Clock CLI

A command-line alarm clock in Python — one-time and recurring alarms, snooze/dismiss, and a
foreground scheduler that rings them. CLI only, no database, **zero runtime dependencies**.

The requirements, design, and trade-offs were written **before** the code — see
**[DESIGN.md](DESIGN.md)**.

## Features

- **One-time, daily, and weekly** alarms (any set of weekdays), each with an optional label.
- **Snooze** (default 9 min) and **dismiss** when an alarm rings.
- **Persistence** to a JSON file (survives restarts) — not a database.
- **Cross-platform ring** — terminal bell always, best-effort system sound on
  macOS / Linux / Windows, graceful fallback.
- **Deterministic tests** — the time logic is pure with an injected clock, so the suite runs
  instantly with no real waiting.

## Requirements

- Python **3.11+**

## Install

```bash
git clone <your-repo-url> && cd alarm-clock-cli
python -m venv .venv && source .venv/bin/activate
pip install -e .          # installs the `alarm` command
alarm --version
```

## Usage

### Add alarms
```bash
alarm add 07:30 --label "Wake up"          # daily (default)
alarm add 08:00 --repeat mon,wed,fri       # specific weekdays
alarm add 14:00 --repeat once --label "Call dentist"   # fires once, then removed
```

### List
```bash
alarm list
```
```
ID      TIME   REPEAT        ON   NEXT            LABEL
74438e  07:30  daily         yes  tomorrow 07:30  Wake up
a88868  08:00  Mon,Wed,Fri   yes  tomorrow 08:00
0617c4  14:00  once          yes  tomorrow 14:00  Call dentist
```

### Manage
```bash
alarm disable 74438e
alarm enable  74438e
alarm remove  0617c4
```

### Run the scheduler (this is what actually rings)
```bash
alarm run                 # rings due alarms; Ctrl-C to stop
alarm run --snooze 5      # 5-minute snooze
```
When an alarm fires you get:
```
⏰  ALARM 07:30 — Wake up

[s]nooze 9m / [d]ismiss:
```
Press `s` to snooze, `d` (or anything else) to dismiss. A `once` alarm is removed after it fires.

## How it works

- **Foreground model:** an alarm rings only while `alarm run` is active in a terminal. This
  is deliberate — it keeps the tool cross-platform and testable without an OS-level daemon
  (see the trade-off in [DESIGN.md](DESIGN.md)).
- **Live management:** `run` re-reads the store each tick, so `add` / `remove` from another
  terminal take effect without restarting it.
- **Where alarms live:** `~/.config/alarmclock/alarms.json`
  (honours `$XDG_CONFIG_HOME`; override entirely with `ALARMCLOCK_STORE=/path/to.json`).
  Writes are atomic; a corrupt file is backed up rather than destroyed.

## Design & decisions (summary)

- **Persisted alarms + a foreground scheduler** — the essential complexity (recurrence,
  persistence, scheduling) without the accidental complexity of a background daemon.
- **Pure scheduler with an injected clock** — `is_due` / `next_fire` take `now` as a
  parameter, so correctness (including midnight wrap and weekday rules) is proven instantly.
- **Structured model, store owns serialization** — the domain stays persistence-agnostic.
- **argparse, zero runtime deps** — sufficient for this CLI; nothing to justify.

Full reasoning and trade-offs: **[DESIGN.md](DESIGN.md)**.

## Testing

```bash
pip install -e ".[dev]"
pytest          # deterministic — injected clock, no real sleeping
ruff check .
```

## Project structure

```
alarm-clock-cli/
├── README.md   DESIGN.md   pyproject.toml   LICENSE
├── src/alarmclock/
│   ├── model.py       # Alarm, Repeat (pure data)
│   ├── scheduler.py   # occurs_on / is_due / next_fire (pure, clock injected)
│   ├── store.py       # atomic JSON persistence
│   ├── ringer.py      # cross-platform ring
│   ├── runner.py      # the foreground scheduler loop
│   └── cli.py         # argparse commands
└── tests/             # scheduler, store, cli, runner
```

## Limitations & next steps

- **Foreground only** — won't ring if no terminal is running it, or while the machine is
  asleep. Productionizing would add an OS scheduler (launchd / systemd / Task Scheduler).
- **Local time** — no timezone/DST handling.

## Author

Built by **Amit Kumar** — [GitHub](https://github.com/amitk-codes) ·
[LinkedIn](https://www.linkedin.com/in/amitkumar-aiml). Licensed under the MIT License.
