"""
updater.py — Release check and update logic for deckery-tray.

State machine:

    IDLE             → "Check for Updates"            clickable → starts check
    CHECKING         → "Checking for updates…"        grayed out
    UP_TO_DATE       → "Up to date (vX.Y.Z)"          grayed out
    UPDATE_AVAILABLE → "Update available: vX.Y.Z"     clickable → runs get.sh
    ERROR            → "Update check failed — retry"  clickable → retries
"""

import json
import logging
import os
import subprocess
import threading
import urllib.request
from enum import Enum, auto

from gi.repository import GLib

log = logging.getLogger("updater")

# ── Paths (derived from this file's location, install-path-agnostic) ──────────
_TRAY_DIR    = os.path.dirname(os.path.abspath(__file__))
_DECKERY_DIR = os.path.dirname(_TRAY_DIR)
_GET_SH      = os.path.join(_DECKERY_DIR, "get.sh")

_GITHUB_TAGS_API = "https://api.github.com/repos/Plasma-Deckery/deckery/tags"


# ── State ─────────────────────────────────────────────────────────────────────

class UpdateState(Enum):
    IDLE             = auto()
    CHECKING         = auto()
    UP_TO_DATE       = auto()
    UPDATE_AVAILABLE = auto()
    ERROR            = auto()


_SENSITIVE = {
    UpdateState.IDLE:             True,
    UpdateState.CHECKING:         False,
    UpdateState.UP_TO_DATE:       True,
    UpdateState.UPDATE_AVAILABLE: True,
    UpdateState.ERROR:            True,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def local_version() -> str:
    """Returns the version tag of the currently checked-out commit (e.g. '0.1.8').
    Uses git describe --exact-match so the result reflects what is actually
    running, not just the highest tag present in the repo.
    Returns 'unknown' if HEAD is not at a tagged commit or git is unavailable."""
    try:
        r = subprocess.run(
            ["git", "-C", _DECKERY_DIR, "describe", "--tags", "--exact-match", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().lstrip("v")
        return "unknown"
    except Exception:
        return "unknown"


def _parse_version(v: str) -> tuple:
    """Parse a version string like '0.1.5' into a comparable tuple (0, 1, 5).
    Returns (0,) for anything that can't be parsed."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


def _fetch_latest_tag() -> str:
    """Fetches the highest semver tag from GitHub. Raises on any error.
    Uses the /tags API so no GitHub Release needs to be published —
    pushing a tag is sufficient to make a new version discoverable."""
    req = urllib.request.Request(
        _GITHUB_TAGS_API,
        headers={"User-Agent": "deckery-tray"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        tags = json.loads(r.read())
    versions = []
    for t in tags:
        name = t["name"].lstrip("v")
        parsed = _parse_version(name)
        if parsed != (0,):
            versions.append((parsed, name))
    if not versions:
        raise ValueError("no version tags found")
    versions.sort(reverse=True)
    return versions[0][1]


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

    # How often to auto-check (seconds). First check after INITIAL_CHECK_DELAY_S.
    CHECK_INTERVAL_S      = 3600
    INITIAL_CHECK_DELAY_S = 30

    def __init__(self, on_state_change):
        self._on_state_change = on_state_change
        self._latest: str | None = None
        self._state = UpdateState.IDLE

        # Schedule initial check, then repeat hourly
        GLib.timeout_add_seconds(self.INITIAL_CHECK_DELAY_S, self._auto_check)

    def _auto_check(self) -> bool:
        """Called by GLib timer. Runs a check if idle, then reschedules."""
        if self._state in (UpdateState.IDLE, UpdateState.UP_TO_DATE, UpdateState.ERROR):
            self._start_check()
        GLib.timeout_add_seconds(self.CHECK_INTERVAL_S, self._auto_check)
        return GLib.SOURCE_REMOVE  # don't repeat this particular timeout

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def state(self) -> UpdateState:
        return self._state

    @property
    def label(self) -> str:
        match self._state:
            case UpdateState.IDLE:
                return "Check for Updates"
            case UpdateState.CHECKING:
                return "Checking for updates…"
            case UpdateState.UP_TO_DATE:
                return "Up to date"
            case UpdateState.UPDATE_AVAILABLE:
                return f"Update available: v{self._latest} — Install"
            case UpdateState.ERROR:
                return "Update check failed — retry"

    @property
    def sensitive(self) -> bool:
        return _SENSITIVE.get(self._state, False)

    def on_clicked(self):
        """Call when the menu item is activated."""
        if self._state in (UpdateState.IDLE, UpdateState.UP_TO_DATE, UpdateState.ERROR):
            self._start_check()
        elif self._state == UpdateState.UPDATE_AVAILABLE:
            self._run_update()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _set_state(self, state: UpdateState):
        if state != self._state:
            log.info("state: %s → %s", self._state.name, state.name)
        self._state = state
        GLib.idle_add(self._on_state_change)

    def _start_check(self):
        log.info("starting update check")
        self._set_state(UpdateState.CHECKING)
        threading.Thread(target=self._check_thread, daemon=True).start()

    def _check_thread(self):
        try:
            latest = _fetch_latest_tag()
            local  = local_version()
            self._latest = latest
            log.info("latest: %s  local: %s", latest, local)
            if local != "unknown" and _parse_version(local) >= _parse_version(latest):
                self._set_state(UpdateState.UP_TO_DATE)
            else:
                self._set_state(UpdateState.UPDATE_AVAILABLE)
        except Exception as e:
            log.warning("update check failed: %s", e)
            self._set_state(UpdateState.ERROR)

    def _run_update(self):
        """Open a terminal and run get.sh — fetches latest tag and re-runs install."""
        log.info("launching update: %s", _GET_SH)
        subprocess.Popen([
            "distrobox-host-exec", "konsole", "--noclose",
            "-e", "bash", _GET_SH,
        ])
