"""
updater.py — Release check and update logic for deckery-tray.

Feature flag: set UPDATES_ENABLED = True once the first release is published
on https://github.com/Plasma-Deckery/deckery/releases

State machine:

    DISABLED         → menu item grayed out, "not yet available"
    IDLE             → "Check for Updates"            clickable → starts check
    CHECKING         → "Checking for updates…"        grayed out
    UP_TO_DATE       → "Up to date (vX.Y.Z)"          grayed out
    UPDATE_AVAILABLE → "Update available: vX.Y.Z"     clickable → runs installer
    ERROR            → "Update check failed — retry"  clickable → retries
"""

import json
import os
import subprocess
import threading
import urllib.request
from enum import Enum, auto

from gi.repository import GLib

# ── Feature flag ──────────────────────────────────────────────────────────────
# Flip to True once the first GitHub release is published.
UPDATES_ENABLED = False

# ── Paths (derived from this file's location, install-path-agnostic) ──────────
_TRAY_DIR    = os.path.dirname(os.path.abspath(__file__))
_DECKERY_DIR = os.path.dirname(_TRAY_DIR)
_VERSION_FILE = os.path.join(_DECKERY_DIR, "VERSION")
_INSTALL_SH   = os.path.join(_DECKERY_DIR, "install.sh")

_GITHUB_API = "https://api.github.com/repos/Plasma-Deckery/deckery/releases/latest"


# ── State ─────────────────────────────────────────────────────────────────────

class UpdateState(Enum):
    DISABLED         = auto()
    IDLE             = auto()
    CHECKING         = auto()
    UP_TO_DATE       = auto()
    UPDATE_AVAILABLE = auto()
    ERROR            = auto()


_SENSITIVE = {
    UpdateState.DISABLED:         False,
    UpdateState.IDLE:             True,
    UpdateState.CHECKING:         False,
    UpdateState.UP_TO_DATE:       False,
    UpdateState.UPDATE_AVAILABLE: True,
    UpdateState.ERROR:            True,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _local_version() -> str:
    try:
        return open(_VERSION_FILE).read().strip()
    except FileNotFoundError:
        return "unknown"


def _fetch_latest_tag() -> str:
    """Fetches the latest release tag from GitHub. Raises on any error."""
    req = urllib.request.Request(
        _GITHUB_API,
        headers={"User-Agent": "deckery-tray"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    return data["tag_name"].lstrip("v")


# ── Updater ───────────────────────────────────────────────────────────────────

class Updater:
    """
    Manages the update-check state machine for the tray menu item.

    All state transitions are dispatched to the GTK main loop via GLib.idle_add,
    so on_state_change() is always called on the main thread.

    Usage:
        updater = Updater(on_state_change=my_callback)
        updater.on_clicked()   # wire to menu item's "activate" signal
    """

    def __init__(self, on_state_change):
        self._on_state_change = on_state_change
        self._latest: str | None = None
        self._state = UpdateState.DISABLED if not UPDATES_ENABLED else UpdateState.IDLE

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def state(self) -> UpdateState:
        return self._state

    @property
    def label(self) -> str:
        match self._state:
            case UpdateState.DISABLED:
                return "Check for Updates — not yet available"
            case UpdateState.IDLE:
                return "Check for Updates"
            case UpdateState.CHECKING:
                return "Checking for updates…"
            case UpdateState.UP_TO_DATE:
                return f"Up to date (v{_local_version()})"
            case UpdateState.UPDATE_AVAILABLE:
                return f"Update available: v{self._latest} — Install"
            case UpdateState.ERROR:
                return "Update check failed — retry"

    @property
    def sensitive(self) -> bool:
        return _SENSITIVE.get(self._state, False)

    def on_clicked(self):
        """Call when the menu item is activated."""
        if self._state in (UpdateState.IDLE, UpdateState.ERROR):
            self._start_check()
        elif self._state == UpdateState.UPDATE_AVAILABLE:
            self._run_install()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _set_state(self, state: UpdateState):
        self._state = state
        GLib.idle_add(self._on_state_change)

    def _start_check(self):
        self._set_state(UpdateState.CHECKING)
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        try:
            latest = _fetch_latest_tag()
            local  = _local_version()
            self._latest = latest
            if local == "unknown" or latest == local:
                self._set_state(UpdateState.UP_TO_DATE)
            else:
                self._set_state(UpdateState.UPDATE_AVAILABLE)
        except Exception:
            self._set_state(UpdateState.ERROR)

    def _run_install(self):
        """Open a terminal and run install.sh so the user can see the output."""
        subprocess.Popen([
            "distrobox-host-exec", "konsole", "--noclose",
            "-e", "bash", _INSTALL_SH,
        ])
