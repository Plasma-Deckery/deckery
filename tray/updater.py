"""
updater.py — Release check and update logic for deckery-tray.

State machine:

    IDLE             → "Check for Updates"            clickable → starts check
    CHECKING         → "Checking for updates…"        grayed out
    UP_TO_DATE       → "Up to date"                   grayed out
    UPDATE_AVAILABLE → "Update available: vX.Y.Z"     clickable → runs get.sh
    AHEAD_OF_RELEASE → "Rollback to vX.Y.Z"           clickable → runs get.sh
    ERROR            → "Update check failed — retry"  clickable → retries

Packaged installs (RPM, see is_packaged_install()) are updated by the system
update, never by get.sh (Issue #78). There the check asks the enabled package
channel instead of git tags (channel.py), so UPDATE_AVAILABLE only appears
when the system update can deliver it. A click opens a dialog in
deckery-tray.py that explains this and, where the image has `ujust`, offers
to start the system update in a terminal. RESTART_REQUIRED (packaged only)
means the update is downloaded and waits for a restart. The hourly check
keeps running in both states. AHEAD_OF_RELEASE needs git and is never reached
on packaged installs.

AHEAD_OF_RELEASE fires when HEAD is not at an exact tag but its commit
timestamp is newer than the latest release tag — i.e. the user is running
a development snapshot that is ahead of the published release. In this case
get.sh is still the correct action (it installs the latest release, which
is the rollback target). The tray icon is NOT changed in this state.
"""

import json
import logging
import os
import subprocess
import threading
import urllib.request
from typing import NamedTuple
from enum import Enum, auto

from gi.repository import GLib

import channel

log = logging.getLogger("updater")

# ── Paths (derived from this file's location, install-path-agnostic) ──────────
_TRAY_DIR    = os.path.dirname(os.path.abspath(__file__))
_DECKERY_DIR = os.path.dirname(_TRAY_DIR)
_GET_SH      = os.path.join(_DECKERY_DIR, "get.sh")

_THIS_FILE   = os.path.abspath(__file__)

_GITHUB_TAGS_API = "https://api.github.com/repos/Plasma-Deckery/deckery/tags"


# ── State ─────────────────────────────────────────────────────────────────────

class UpdateState(Enum):
    IDLE             = auto()
    CHECKING         = auto()
    UP_TO_DATE       = auto()
    UPDATE_AVAILABLE = auto()
    AHEAD_OF_RELEASE = auto()
    RESTART_REQUIRED = auto()   # packaged only: update downloaded, not booted
    ERROR            = auto()


_SENSITIVE = {
    UpdateState.IDLE:             True,
    UpdateState.CHECKING:         False,
    UpdateState.UP_TO_DATE:       True,
    UpdateState.UPDATE_AVAILABLE: True,
    UpdateState.AHEAD_OF_RELEASE: True,
    UpdateState.RESTART_REQUIRED: True,
    UpdateState.ERROR:            True,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _in_git_checkout(path: str) -> bool:
    """True if path or any parent directory contains .git (a directory in a
    clone, a file in a worktree)."""
    d = path
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return True
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def _rpm_owner_version(path: str) -> str | None:
    """Version of the RPM that owns path, or None if no package owns it
    (or rpm is missing)."""
    try:
        r = subprocess.run(
            ["rpm", "-qf", "--qf", "%{VERSION}", path],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return None


_packaged: bool | None = None


def is_packaged_install() -> bool:
    """True if this tray was installed by a package (RPM) rather than from a
    source checkout. Decides whether the tray may update itself (Issue #78).

    Packaged means both: no git checkout around the running tray, and the
    running updater.py is owned by an RPM. Both conditions use the running
    file, so a host with a source install and a layered RPM is classified by
    whichever tray is actually running. Requiring the git check first keeps
    every source install on today's path without even calling rpm.

    Cached: the answer cannot change while the process runs."""
    global _packaged
    if _packaged is None:
        _packaged = (not _in_git_checkout(_TRAY_DIR)
                     and _rpm_owner_version(_THIS_FILE) is not None)
        log.info("install type: %s", "packaged" if _packaged else "source")
    return _packaged


# ── User-facing text for packaged installs ────────────────────────────────────
#
# Plain words for non-technical users: no package or distribution jargon.

def packaged_label(state: UpdateState, version: str | None, can_update: bool) -> str | None:
    """Menu label for packaged installs where it differs from source installs,
    else None."""
    if state == UpdateState.UPDATE_AVAILABLE:
        if can_update:
            return f"Update available: v{version}"
        return f"Update available: v{version} — comes with your next system update"
    if state == UpdateState.RESTART_REQUIRED:
        return f"Restart to finish updating to v{version}"
    return None


class Hint(NamedTuple):
    title: str
    text:  str


def packaged_hint(state: UpdateState, version: str | None, can_update: bool) -> Hint:
    """Title and text of the dialog a click opens on packaged installs."""
    v = f"Deckery v{version}" if version else "A new version of Deckery"
    if state == UpdateState.RESTART_REQUIRED:
        return Hint(
            "Restart to finish the update",
            f"{v} has already been downloaded. Restart your device to start "
            "using it.",
        )
    if can_update:
        return Hint(
            "Update available",
            f"{v} is ready. Deckery is updated together with the rest of your "
            "system.\n\n"
            "Update now updates your whole system. This can take a while, and "
            "you need to restart your device afterwards.",
        )
    return Hint(
        "Deckery updates come with your system updates",
        f"{v} is ready. On this system, Deckery is updated together with the "
        "rest of your system, so there is nothing to install here.\n\n"
        "It will be installed with your next system update. Updates take "
        "effect after you restart your device.",
    )


UPDATE_NOW_BUTTON = "Update now"
LATER_BUTTON      = "Later"


def local_version() -> str:
    """Returns the version of the currently running Deckery installation.

    Tries two sources in order:
    1. git describe --exact-match HEAD  — works for source/install.sh installs
       where the tray runs from a checked-out repo at a tagged commit.
    2. rpm -q deckery                   — works for RPM installs (Copr/Bazzite);
       the tray lives under /usr/lib/deckery/tray/ with no .git present.

    Returns 'unknown' if both sources fail or the version cannot be parsed."""
    # 1. Git source install
    try:
        r = subprocess.run(
            ["git", "-C", _DECKERY_DIR, "describe", "--tags", "--exact-match", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip().lstrip("v")
    except Exception:
        pass

    # 2. RPM install fallback (deckery meta-package)
    try:
        r = subprocess.run(
            ["rpm", "-q", "deckery", "--qf", "%{VERSION}"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass

    # 3. The package that owns this tray (deckery-tray), for systems where the
    #    deckery meta-package is not installed. Same version scheme.
    v = _rpm_owner_version(_THIS_FILE)
    if v:
        return v

    return "unknown"


def _parse_version(v: str) -> tuple:
    """Parse a version string like '0.1.5' into a comparable tuple (0, 1, 5).
    Returns (0,) for anything that can't be parsed."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


def _local_commit_timestamp() -> int | None:
    """Returns the Unix commit timestamp of HEAD, or None on error."""
    try:
        r = subprocess.run(
            ["git", "-C", _DECKERY_DIR, "log", "-1", "--format=%ct", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return int(r.stdout.strip())
    except Exception:
        pass
    return None


def _tag_commit_timestamp(tag: str) -> int | None:
    """Returns the Unix commit timestamp of the given tag (e.g. '0.3.0'), or None on error.
    Tries the local repo first (fast); falls back to None if the tag is not fetched."""
    try:
        r = subprocess.run(
            ["git", "-C", _DECKERY_DIR, "log", "-1", "--format=%ct", f"v{tag}"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return int(r.stdout.strip())
    except Exception:
        pass
    return None


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

    def __init__(self, on_state_change, packaged: bool | None = None):
        self._on_state_change = on_state_change
        self._packaged = is_packaged_install() if packaged is None else packaged
        self._latest: str | None = None
        self._state = UpdateState.IDLE

        # Schedule initial check, then repeat hourly
        GLib.timeout_add_seconds(self.INITIAL_CHECK_DELAY_S, self._auto_check)

    def _auto_check(self) -> bool:
        """Called by GLib timer. Runs a check if idle, then reschedules.

        Source installs stop checking once an update is offered: the next step
        is the user's click. Packaged installs have no such step, so they keep
        checking and the label follows newer releases."""
        recheck = {UpdateState.IDLE, UpdateState.UP_TO_DATE, UpdateState.ERROR}
        if self._packaged:
            recheck |= {UpdateState.UPDATE_AVAILABLE, UpdateState.RESTART_REQUIRED}
        if self._state in recheck:
            self._start_check()
        GLib.timeout_add_seconds(self.CHECK_INTERVAL_S, self._auto_check)
        return GLib.SOURCE_REMOVE  # don't repeat this particular timeout

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def state(self) -> UpdateState:
        return self._state

    @property
    def packaged(self) -> bool:
        """True on packaged installs: updates come from the system update."""
        return self._packaged

    @property
    def latest(self) -> str | None:
        return self._latest

    @property
    def system_update_command(self) -> list[str] | None:
        """Packaged only: argv that runs the system update in a terminal, or
        None if this system cannot offer it (no ujust or no terminal)."""
        if not self._packaged:
            return None
        return channel.system_update_command()

    @property
    def hint(self) -> "Hint":
        return packaged_hint(self._state, self._latest,
                             self.system_update_command is not None)

    @property
    def label(self) -> str:
        if self._packaged:
            text = packaged_label(self._state, self._latest,
                                  self.system_update_command is not None)
            if text:
                return text
        match self._state:
            case UpdateState.IDLE:
                return "Check for Updates"
            case UpdateState.CHECKING:
                return "Checking for updates…"
            case UpdateState.UP_TO_DATE:
                return "Up to date"
            case UpdateState.UPDATE_AVAILABLE:
                return f"Update available: v{self._latest} — Install"
            case UpdateState.AHEAD_OF_RELEASE:
                return f"Rollback to v{self._latest}"
            case UpdateState.RESTART_REQUIRED:
                return f"Restart to finish updating to v{self._latest}"
            case UpdateState.ERROR:
                return "Update check failed — retry"

    @property
    def sensitive(self) -> bool:
        return _SENSITIVE.get(self._state, False)

    def on_clicked(self):
        """Call when the menu item is activated. On packaged installs the
        UPDATE_AVAILABLE click is handled by the tray (explanation dialog);
        here it does nothing."""
        if self._state in (UpdateState.IDLE, UpdateState.UP_TO_DATE, UpdateState.ERROR):
            self._start_check()
        elif self._packaged:
            return
        elif self._state in (UpdateState.UPDATE_AVAILABLE, UpdateState.AHEAD_OF_RELEASE):
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
        if self._packaged:
            self._check_packaged()
            return
        try:
            latest = _fetch_latest_tag()
            local  = local_version()
            self._latest = latest
            log.info("latest: %s  local: %s", latest, local)
            if local != "unknown" and _parse_version(local) >= _parse_version(latest):
                self._set_state(UpdateState.UP_TO_DATE)
            elif local == "unknown":
                # HEAD is not on an exact tag. Check whether it is *ahead* of the
                # latest release (dev snapshot) or *behind* it (partial checkout).
                local_ts = _local_commit_timestamp()
                tag_ts   = _tag_commit_timestamp(latest)
                if local_ts and tag_ts and local_ts > tag_ts:
                    log.info("ahead of release: local ts %s > tag ts %s", local_ts, tag_ts)
                    self._set_state(UpdateState.AHEAD_OF_RELEASE)
                else:
                    self._set_state(UpdateState.UPDATE_AVAILABLE)
            else:
                self._set_state(UpdateState.UPDATE_AVAILABLE)
        except Exception as e:
            log.warning("update check failed: %s", e)
            self._set_state(UpdateState.ERROR)

    def _check_packaged(self):
        """Channel-aware check (channel.py): compares the installed package
        with the newest build the enabled channel offers, not with git tags."""
        try:
            result = channel.check(_THIS_FILE)
        except Exception as e:
            log.warning("update check failed: %s", e)
            self._set_state(UpdateState.ERROR)
            return
        self._latest = result.version
        self._set_state({
            "up_to_date":       UpdateState.UP_TO_DATE,
            "update_available": UpdateState.UPDATE_AVAILABLE,
            "restart_required": UpdateState.RESTART_REQUIRED,
        }[result.status])

    def start_system_update(self) -> bool:
        """Packaged only: open a terminal running the system update. Returns
        False if this system cannot offer it. Re-checks once the terminal
        closes, so the menu moves on to "Restart to finish…"."""
        argv = self.system_update_command
        if argv is None:
            return False
        log.info("starting system update: %s", channel.describe(argv))
        try:
            proc = subprocess.Popen(argv)
        except OSError as e:
            log.warning("could not start system update: %s", e)
            return False

        def _wait():
            proc.wait()
            GLib.idle_add(self._recheck_after_update)
        threading.Thread(target=_wait, daemon=True).start()
        return True

    def _recheck_after_update(self) -> bool:
        if self._state != UpdateState.CHECKING:
            self._start_check()
        return GLib.SOURCE_REMOVE

    def _run_update(self):
        """Open a terminal and run get.sh — fetches latest tag and re-runs install.
        Never on packaged installs: get.sh would build a second installation
        whose user units shadow the package's (Issue #78)."""
        if self._packaged:
            log.warning("packaged install — not running get.sh")
            return
        log.info("launching update: %s", _GET_SH)
        subprocess.Popen([
            "distrobox-host-exec", "konsole", "--noclose",
            "-e", "bash", _GET_SH,
        ])
