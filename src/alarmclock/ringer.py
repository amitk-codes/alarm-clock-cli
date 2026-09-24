"""Cross-platform ringing: a banner + terminal bell + best-effort OS audio.

The terminal bell is the guaranteed alert; OS audio is a best-effort extra that fails
silently if unavailable. Ringing is start/stop (not one-shot) so it keeps sounding while
the run loop waits for the user to snooze or dismiss.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import threading
from typing import Protocol

from .model import Alarm

_DEVNULL = subprocess.DEVNULL


class Ringer(Protocol):
    def start(self, alarm: Alarm) -> None: ...
    def stop(self) -> None: ...


def _play_sound() -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["afplay", "/System/Library/Sounds/Glass.aiff"],
                check=False, timeout=3, stdout=_DEVNULL, stderr=_DEVNULL,
            )
        elif system == "Linux":
            for player, sound in (
                ("paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"),
                ("aplay", "/usr/share/sounds/alsa/Front_Center.wav"),
            ):
                if shutil.which(player):
                    subprocess.run(
                        [player, sound],
                        check=False, timeout=3, stdout=_DEVNULL, stderr=_DEVNULL,
                    )
                    break
        elif system == "Windows":
            import winsound

            winsound.MessageBeep()
    except Exception:
        pass  # the terminal bell already covers the alert


class ConsoleRinger:
    """Rings in the terminal: a banner, then a bell/sound loop until stopped."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, alarm: Alarm) -> None:
        label = f" — {alarm.label}" if alarm.label else ""
        print(f"\n⏰  ALARM {alarm.time:%H:%M}{label}\n", flush=True)
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            sys.stdout.write("\a")
            sys.stdout.flush()
            _play_sound()
            self._stop.wait(1.0)
