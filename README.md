# Alarm Clock CLI

A command-line alarm clock in Python — one-time and recurring alarms, snooze, and a
foreground scheduler that rings them. CLI only, no database, zero runtime dependencies.

See **[DESIGN.md](DESIGN.md)** for the requirements, design, and trade-offs (written before
the code).

## Install (development)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alarm --version
```

## Status

Scaffold in place (`alarm` command installs and runs). Commands and the scheduler land
next — see the plan in [DESIGN.md](DESIGN.md).
