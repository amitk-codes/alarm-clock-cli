# Alarm Clock CLI — Requirements, Design & Plan

This is the pre-coding design: what I'm building, why it's shaped this way, and the
trade-offs I made. It is committed **before** any code, on purpose.

---

## 1. Requirements

### Problem statement
A command-line alarm clock. A user creates alarms (one-time or recurring), manages them,
and has them **ring** at the right time. CLI only — no web UI, no database, Python only.

The interesting problems here aren't "compare two times"; they are:
1. **How does an alarm ring in a terminal app?**
2. **How do you make time-based behavior deterministically testable** (no waiting for wall
   time, no flaky tests)?

### Functional requirements
1. **Create** an alarm at a time (`HH:MM`, 24h, local), with an optional label and a schedule:
   - **once** — fires at the next occurrence of that time, then auto-removes.
   - **daily** — every day.
   - **weekly** — a set of weekdays (e.g. Mon–Fri).
2. **List** alarms with their next fire time and enabled/disabled state.
3. **Remove**, **enable**, **disable** an alarm by id.
4. **Run** — a foreground scheduler that rings due alarms; on ring the user can **snooze**
   (default 9 minutes) or **dismiss**.
5. **Persist** alarms across invocations in a JSON file (not a database).

### Non-functional requirements
- **Deterministic, fast tests** for all time logic (no real sleeping).
- **Cross-platform** best-effort ring (macOS / Linux / Windows) with graceful fallback.
- **Zero runtime dependencies** (stdlib only). Dev tooling: `pytest` + `ruff`.
- Installs as a real `alarm` command; clear `--help`; friendly validation errors.
- Robust to a missing or corrupt store file.

### Explicit non-goals (and why)
- **Background daemon / ring when no terminal is open** — requires OS-specific service
  setup (launchd / systemd / Task Scheduler); disproportionate effort and brittle to test.
  Documented below as the productionization path.
- **Timezone / DST correctness** — local time only; noted as a known limitation.
- **GUI, third-party sound libraries, PyPI publishing** — out of scope.

### Resolved assumptions / decisions
- "No database" ⇒ a JSON **file** is acceptable
  (`$XDG_CONFIG_HOME/alarmclock/alarms.json`, default `~/.config/alarmclock/alarms.json`).
- An alarm rings only while `alarm run` is active in a terminal. This is a **deliberate,
  stated model**, not an oversight.
- `run` **re-reads the store each tick**, so `add` / `remove` from another terminal take
  effect live — no IPC or daemon needed.

---

## 2. Design

### Architecture (layers; dependencies point inward)
```
cli.py ────┐                        model.py      ← Alarm, Schedule (pure data)
           ├─► store.py (JSON)      scheduler.py  ← pure time logic (clock injected)
runner.py ─┴─► ringer.py (sound)
```
- **Domain** (`model`, `scheduler`) is pure and I/O-free.
- **Adapters** (`store`, `ringer`, `cli`) touch the outside world.
- `runner` composes them into the run loop.
- Everything time- or environment-dependent is **injected** (a `now()` callable, a
  `sleep()` callable, a ringer), so tests are deterministic.

### Domain model
```
Alarm:    id, label, time ("HH:MM"), schedule, enabled, created_at
Schedule: ONCE | DAILY | WEEKLY(weekdays: set[int]  # 0=Mon … 6=Sun)
```

### Scheduler — pure functions (the heart, fully unit-tested)
- `occurs_on(alarm, date) -> bool` — does it fire on that weekday?
- `is_due(alarm, now, last_fired_minute) -> bool` — fires this minute, guarded so it rings
  **once per occurrence**.
- `next_fire(alarm, now) -> datetime | None` — next fire time (for `list` and `once` expiry).

"Does it ring now / when next" is decided entirely by these, with `now` passed in — so a
test can assert "a Mon–Fri 07:30 alarm is due Tue 07:30 but not Sat 07:30" with **no clock
and no sleep**.

### CLI surface (argparse subcommands)
```
alarm add 07:30 --label "Wake up" --repeat daily
alarm add 08:00 --repeat mon,tue,wed,thu,fri
alarm add 14:00 --once
alarm list
alarm remove <id>   |   alarm enable <id>   |   alarm disable <id>
alarm run [--snooze 9]
```

### Persistence
JSON array of alarms. **Atomic writes** (temp file + `os.replace`) to avoid corruption.
Missing/corrupt file → treated as empty with a warning. Single-user assumption noted.

### Ringing (honest cross-platform)
`ringer.ring(alarm)`: print a clear banner + emit the terminal bell repeatedly, **and**
best-effort audio — macOS `afplay` a system sound, Linux `paplay`/`aplay`, Windows
`winsound` — each via stdlib/`subprocess`, **falling back to the bell** if unavailable.
No third-party sound dependency.

### The run loop
Tick each second: reload store → for each enabled alarm, `is_due?` → if yes, ring. While
ringing, a small thread keeps beeping while the loop prompts `[s]nooze / [d]ismiss`.
Snooze schedules a transient re-fire at `now + N`; a `once` alarm is removed after firing.
`Ctrl-C` exits cleanly.

### Edge cases handled
Time already passed today → next valid occurrence; exact-minute / midnight boundaries;
duplicate alarms allowed; invalid `HH:MM` / weekday → validation error; corrupt store →
recover; machine asleep / terminal closed → won't ring (documented).

---

## 3. Implementation plan (ordered, test-first — one commit each)

1. `docs: requirements, design & implementation plan` — this file, `.gitignore`, `LICENSE`.
2. `chore: project scaffold` — `pyproject.toml` (`alarm` entry point, ruff/pytest), package skeleton, README stub.
3. `feat: alarm model and scheduler` — `model.py`, `scheduler.py` + **tests written first**.
4. `feat: JSON file persistence` — `store.py` + tests (round-trip, atomic, corrupt recovery).
5. `feat: CLI commands` — `cli.py`, `__main__.py` (add/list/remove/enable/disable) + tests.
6. `feat: ring + run loop with snooze/dismiss` — `ringer.py`, `runner.py` + tests (fake clock).
7. `docs: README and final validation` — README, `ruff` clean, one real end-to-end ring.

### Testing strategy (the headline signal)
- **Unit — scheduler:** parametrized, injected `now`. The bulk of coverage.
- **Store:** round-trip + atomic write + corrupt-file recovery.
- **CLI:** parse + dispatch against a temp file.
- **Runner:** a fake clock advances instantly (injected `sleep` moves fake time) + a fake
  ringer — assert fire timing, snooze re-fire, once-removal. **Zero real sleeps.**

### Repo layout
```
alarm-clock-cli/
├── README.md   DESIGN.md   pyproject.toml   LICENSE
├── src/alarmclock/{__main__,cli,model,scheduler,store,ringer,runner}.py
└── tests/{test_scheduler,test_store,test_cli,test_runner}.py
```

### Risks & validation
- **Sound portability** → validate on the target OS; simulate a missing player to prove the
  fallback path.
- **Time correctness** → deterministic tests + one live end-to-end ring.
- **Foreground-only** → documented, with the OS-scheduler daemon as the "what I'd do next."
