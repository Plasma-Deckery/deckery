"""
steam_config_watcher.py — Detects changes to the Steam Desktop Controller Config.

Steam overwrites desktop_neptune.vdf on every client start, reverting to its
defaults and breaking Deckery's input remapping. This module detects content
changes and surfaces them in the tray with manual fix and lock actions.

Detection:
  • Startup:   SHA-256 hash check + lsattr immutable flag check
  • Runtime:   inotify directory watch via GLib.io_add_watch (no extra thread)
               catches Steam's rename-then-write update sequence
  • Sentinel:  terminal scripts touch ~/.config/deckery/.steam-lock-sentinel
               after chattr +i / -i, triggering an immediate recheck
               (chattr uses ioctl(FS_IOC_SETFLAGS) which does not fire inotify)
  • Fallback:  poll every 30s for external chattr changes (manual, Steam update)

States:
    locked      target matches canonical copy and is immutable (chattr +i)  — green
    unlocked    target matches but is not locked                             — yellow
    overwritten target does not match canonical copy                         — red
    no_source   canonical file missing from ~/.config/makima/
"""

import ctypes
import hashlib
import logging
import os
import struct
import subprocess

from gi.repository import GLib, Gio

log = logging.getLogger("steam_config_watcher")


# ── Paths ─────────────────────────────────────────────────────────────────────

_SOURCE    = os.path.expanduser("~/.config/makima/desktop_neptune.vdf")
_TARGET    = os.path.expanduser(
    "~/.local/share/Steam/controller_base/desktop_neptune.vdf"
)
_WATCH_DIR = os.path.dirname(_TARGET)
_SENTINEL  = os.path.expanduser("~/.config/deckery/.steam-lock-sentinel")


# ── File state helpers ────────────────────────────────────────────────────────

def _sha256(path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _files_match() -> bool:
    s, t = _sha256(_SOURCE), _sha256(_TARGET)
    return s is not None and t is not None and s == t


def _is_locked() -> bool:
    """Return True if the target file has the chattr +i immutable flag."""
    try:
        r = subprocess.run(
            ["lsattr", _TARGET], capture_output=True, text=True, timeout=2
        )
        if r.returncode == 0 and r.stdout.strip():
            return "i" in r.stdout.split()[0]
        return False
    except Exception:
        return False


# ── Minimal inotify via ctypes + GLib.io_add_watch ───────────────────────────
#
# Watches the parent directory for IN_CLOSE_WRITE and IN_MOVED_TO events.
# This survives Steam's rename-then-write update sequence.
#
# Note: IN_ATTRIB on the file itself does NOT fire for chattr +i/-i because
# chattr uses ioctl(FS_IOC_SETFLAGS) which bypasses the fsnotify subsystem on
# most ext4 configurations. Lock state changes are handled via sentinel file.

_libc           = ctypes.CDLL("libc.so.6", use_errno=True)
_EVENT_HDR      = struct.Struct("iIII")   # wd, mask, cookie, len
_IN_CLOSE_WRITE = 0x00000008
_IN_MOVED_TO    = 0x00000080


def _inotify_init(watch_dir: str) -> tuple[int, int] | None:
    """
    Create an inotify fd watching watch_dir for content changes.
    Returns (fd, wd) or None on failure.
    """
    fd = _libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
    if fd < 0:
        return None
    wd = _libc.inotify_add_watch(
        fd, watch_dir.encode(), _IN_CLOSE_WRITE | _IN_MOVED_TO
    )
    if wd < 0:
        os.close(fd)
        return None
    return fd, wd


def _drain_inotify(fd: int) -> list[str]:
    """Drain pending inotify events, return list of filenames."""
    names = []
    try:
        data = os.read(fd, 65536)
    except (BlockingIOError, OSError):
        return names
    offset = 0
    while offset + _EVENT_HDR.size <= len(data):
        _, _, _, length = _EVENT_HDR.unpack_from(data, offset)
        offset += _EVENT_HDR.size
        if length > 0:
            raw = data[offset: offset + length]
            names.append(raw.rstrip(b"\x00").decode(errors="replace"))
            offset += length
    return names


# ── Terminal helper ───────────────────────────────────────────────────────────

def _open_terminal(subtitle: str, body: str) -> None:
    """Open a Konsole terminal with the standard Deckery header and given body."""
    sep = "─" * len(subtitle)
    script = "\n".join([
        "echo ''",
        "echo '  ╔══════════════════════════════════════╗'",
        "echo '  ║       Deckery — Steam Config         ║'",
        "echo '  ╚══════════════════════════════════════╝'",
        "echo ''",
        f"echo '  {subtitle}'",
        f"echo '  {sep}'",
        "echo ''",
        body,
        "echo ''",
        "read -p '  Press Enter to close...'",
    ])
    subprocess.Popen([
        "distrobox-host-exec", "konsole", "--noclose",
        "-e", "bash", "-c", script,
    ])


# ── Watcher ───────────────────────────────────────────────────────────────────

class SteamConfigWatcher:
    """
    Watches the Steam Desktop Controller Config for content changes and lock state.

    State machine:
        locked      → green  — file matches canonical copy and is immutable
        unlocked    → yellow — file matches but not locked
        overwritten → red    — file does not match canonical copy
        no_source           — canonical file missing from ~/.config/makima/

    All state transitions run on the GTK main thread (GLib.io_add_watch /
    GLib.idle_add), so on_state_change() is always safe to call from any context.
    """

    def __init__(self, on_state_change):
        self._on_state_change         = on_state_change
        self._state                   = "unlocked"
        self._inotify_fd: int | None  = None
        self._inotify_source: int | None = None
        self._sentinel_monitor        = None
        self._poll_source: int | None = None

        self._activate()

    # ── Public interface ──────────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    @property
    def label(self) -> str:
        match self._state:
            case "locked":      return "Steam config: locked"
            case "unlocked":    return "Steam config: unlocked"
            case "overwritten": return "Steam config: Fix and Lock"
            case "no_source":   return "Steam config: source missing"
            case _:             return "Steam config"

    def open_lock_terminal(self) -> None:
        """Open a terminal that locks the file with chattr +i (content already correct)."""
        _open_terminal(
            "Locking Steam Controller Config",
            "\n".join([
                "echo '  The Deckery controller config is in place but the file is not locked.'",
                "echo '  Locking it prevents Steam from overwriting it on startup.'",
                "echo ''",
                f"sudo chattr +i '{_TARGET}'"
                f" && echo '  ✓ Config locked.' && touch '{_SENTINEL}'"
                f" || echo '  ✗ ERROR: could not lock — check permissions.'",
            ]),
        )
        log.info("opened lock terminal")

    def open_fix_and_lock_terminal(self) -> None:
        """Open a terminal that copies the canonical VDF and locks it with chattr +i."""
        _open_terminal(
            "Restoring and Locking Steam Controller Config",
            "\n".join([
                "echo '  Steam has overwritten the controller config with its defaults,'",
                "echo '  which breaks Deckery'\"'\"'s input remapping.'",
                "echo ''",
                "echo '  Restoring the Deckery config and locking the file so Steam'",
                "echo '  cannot overwrite it again on the next start.'",
                "echo ''",
                f"cp '{_SOURCE}' '{_TARGET}' && sudo chattr +i '{_TARGET}'"
                f" && echo '  ✓ Config restored and locked.' && touch '{_SENTINEL}'"
                f" || echo '  ✗ ERROR: operation failed — check permissions.'",
            ]),
        )
        log.info("opened fix-and-lock terminal")

    def open_unlock_terminal(self) -> None:
        """Open a terminal that removes the chattr +i lock."""
        _open_terminal(
            "Unlocking Steam Controller Config for Update",
            "\n".join([
                "echo '  The Steam controller config is currently locked (chattr +i).'",
                "echo '  This prevents Steam from overwriting it — but a Steam client'",
                "echo '  update will fail while the lock is active.'",
                "echo ''",
                "echo '  Install the Steam update, then restore and re-lock via:'",
                "echo '    Tray menu  →  Steam config: Fix and Lock'",
                "echo ''",
                f"sudo chattr -i '{_TARGET}'"
                f" && echo '  ✓ Config unlocked. You can now install the Steam update.' && touch '{_SENTINEL}'"
                f" || echo '  ✗ ERROR: could not unlock — check permissions.'",
            ]),
        )
        log.info("opened unlock terminal")

    def stop(self) -> None:
        """Clean shutdown — called on tray exit."""
        self._deactivate()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        if state != self._state:
            log.info("state: %s → %s", self._state, state)
        self._state = state
        GLib.idle_add(self._on_state_change)

    def _recheck(self) -> None:
        """Determine current state from disk and notify."""
        if not os.path.exists(_SOURCE):
            self._set_state("no_source")
        elif not _files_match():
            self._set_state("overwritten")
        elif _is_locked():
            self._set_state("locked")
        else:
            self._set_state("unlocked")

    def _activate(self) -> None:
        self._recheck()

        # inotify: content changes (Steam overwriting the file)
        result = _inotify_init(_WATCH_DIR)
        if result is not None:
            fd, wd = result
            self._inotify_fd     = fd
            self._inotify_source = GLib.io_add_watch(fd, GLib.IO_IN, self._on_inotify)
            log.info("inotify armed on %s (wd=%d)", _WATCH_DIR, wd)
        else:
            log.warning("inotify_init failed — content changes will not be detected")

        # Sentinel monitor: immediate recheck after our own terminal actions
        os.makedirs(os.path.dirname(_SENTINEL), exist_ok=True)
        sentinel = Gio.File.new_for_path(_SENTINEL)
        self._sentinel_monitor = sentinel.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self._sentinel_monitor.connect("changed", self._on_sentinel_changed)
        log.info("sentinel monitor armed on %s", _SENTINEL)

        # Fallback poll: catches external chattr changes (manual, Steam update)
        self._poll_source = GLib.timeout_add_seconds(30, self._on_poll)

    def _deactivate(self) -> None:
        if self._inotify_source is not None:
            GLib.source_remove(self._inotify_source)
            self._inotify_source = None
        if self._inotify_fd is not None:
            os.close(self._inotify_fd)
            self._inotify_fd = None
        if self._sentinel_monitor is not None:
            self._sentinel_monitor.cancel()
            self._sentinel_monitor = None
        if self._poll_source is not None:
            GLib.source_remove(self._poll_source)
            self._poll_source = None
        log.info("watcher deactivated")

    def _on_inotify(self, fd: int, _condition) -> bool:
        """GLib.io_add_watch callback — runs on GTK main thread."""
        names = _drain_inotify(fd)
        if "desktop_neptune.vdf" in names:
            log.debug("inotify: desktop_neptune.vdf changed")
            self._recheck()
        return GLib.SOURCE_CONTINUE

    def _on_sentinel_changed(self, _monitor, _file, _other, _event) -> None:
        """Fires when a terminal script touches the sentinel file after chattr."""
        log.debug("sentinel changed — rechecking lock state")
        self._recheck()

    def _on_poll(self) -> bool:
        """Periodic fallback — catches external chattr changes inotify misses."""
        self._recheck()
        return GLib.SOURCE_CONTINUE
