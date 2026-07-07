"""
test_steam_config_watcher.py — Tests for SteamConfigWatcher.

Covers:
  • State machine (_recheck): all four states
  • Event paths: inotify, sentinel, poll — each triggers the right recheck
  • Terminal actions: subprocess.Popen receives the correct script content
  • Label property: all states produce a non-empty label

GLib and Gio are mocked in conftest.py. _inotify_init is mocked per-test
so no kernel syscall is made.
"""

import sys
import os
import struct
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, call
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import steam_config_watcher as scw
from steam_config_watcher import SteamConfigWatcher, _SOURCE, _TARGET, _SENTINEL


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pack_inotify_event(wd: int, name: str = "") -> bytes:
    """Build a synthetic inotify event binary blob for testing _drain_inotify."""
    name_bytes = (name.encode() + b"\x00") if name else b""
    return struct.pack("iIII", wd, 0, 0, len(name_bytes)) + name_bytes


def _lsattr_result(attrs: str, returncode: int = 0):
    """Build a mock subprocess.CompletedProcess for lsattr output."""
    r = MagicMock()
    r.returncode = returncode
    r.stdout = f"{attrs} {_TARGET}\n" if attrs else ""
    return r


# ── _drain_inotify: raw byte parsing ─────────────────────────────────────────

class TestDrainInotify:
    """
    _drain_inotify reads raw inotify bytes and returns filenames.
    Tests use struct.pack to build synthetic event blobs — no kernel needed.
    """

    def test_single_event_returns_filename(self):
        data = _pack_inotify_event(wd=1, name="desktop_neptune.vdf")
        with patch("os.read", return_value=data):
            names = scw._drain_inotify(fd=5)
        assert names == ["desktop_neptune.vdf"]

    def test_multiple_events_in_one_read(self):
        data = (
            _pack_inotify_event(wd=1, name="desktop_neptune.vdf")
            + _pack_inotify_event(wd=1, name="other.vdf")
        )
        with patch("os.read", return_value=data):
            names = scw._drain_inotify(fd=5)
        assert names == ["desktop_neptune.vdf", "other.vdf"]

    def test_nameless_event_returns_empty_list(self):
        # Attribute-change events (IN_ATTRIB) have len=0 and no name field.
        data = _pack_inotify_event(wd=1, name="")
        with patch("os.read", return_value=data):
            names = scw._drain_inotify(fd=5)
        assert names == []

    def test_null_bytes_are_stripped_from_name(self):
        # inotify pads names with null bytes to align to 4 bytes.
        name_bytes = b"file.vdf\x00\x00\x00\x00"
        header = struct.pack("iIII", 1, 0, 0, len(name_bytes))
        with patch("os.read", return_value=header + name_bytes):
            names = scw._drain_inotify(fd=5)
        assert names == ["file.vdf"]

    def test_blocking_io_error_returns_empty(self):
        with patch("os.read", side_effect=BlockingIOError):
            names = scw._drain_inotify(fd=5)
        assert names == []

    def test_os_error_returns_empty(self):
        with patch("os.read", side_effect=OSError):
            names = scw._drain_inotify(fd=5)
        assert names == []

    def test_empty_data_returns_empty(self):
        with patch("os.read", return_value=b""):
            names = scw._drain_inotify(fd=5)
        assert names == []


# ── _is_locked: lsattr output parsing ────────────────────────────────────────

class TestIsLocked:
    """
    _is_locked runs lsattr and checks for the 'i' (immutable) flag.
    All subprocess calls are mocked.
    """

    def test_immutable_flag_returns_true(self):
        with patch.object(scw.subprocess, "run",
                          return_value=_lsattr_result("----i---------e-------")):
            assert scw._is_locked() is True

    def test_no_immutable_flag_returns_false(self):
        with patch.object(scw.subprocess, "run",
                          return_value=_lsattr_result("----------------------")):
            assert scw._is_locked() is False

    def test_lsattr_failure_returns_false(self):
        with patch.object(scw.subprocess, "run",
                          return_value=_lsattr_result("", returncode=1)):
            assert scw._is_locked() is False

    def test_empty_stdout_returns_false(self):
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        with patch.object(scw.subprocess, "run", return_value=r):
            assert scw._is_locked() is False

    def test_exception_returns_false(self):
        with patch.object(scw.subprocess, "run", side_effect=FileNotFoundError):
            assert scw._is_locked() is False

    def test_timeout_returns_false(self):
        with patch.object(scw.subprocess, "run", side_effect=TimeoutError):
            assert scw._is_locked() is False


# ── Fixture ───────────────────────────────────────────────────────────────────

@contextmanager
def _make_watcher(*, exists=True, match=True, locked=True):
    """
    Construct a SteamConfigWatcher with mocked filesystem state.

    Patches applied during construction (and available in the with-block):
      - os.path.exists → exists
      - _files_match   → match
      - _is_locked     → locked
      - _inotify_init  → returns fake (fd=5, wd=1), no kernel syscall
    """
    callback = MagicMock()
    with patch.object(scw, "_inotify_init",  return_value=(5, 1)), \
         patch.object(scw.os.path, "exists", return_value=exists), \
         patch.object(scw, "_files_match",   return_value=match), \
         patch.object(scw, "_is_locked",     return_value=locked):
        watcher = SteamConfigWatcher(on_state_change=callback)
        yield watcher, callback


# ── State machine ─────────────────────────────────────────────────────────────

class TestRecheck:
    """_recheck() maps filesystem state to the correct watcher state."""

    def test_no_source_when_file_missing(self):
        with _make_watcher(exists=False) as (w, _):
            assert w.state == "no_source"

    def test_overwritten_when_content_differs(self):
        with _make_watcher(exists=True, match=False) as (w, _):
            assert w.state == "overwritten"

    def test_locked_when_content_matches_and_immutable(self):
        with _make_watcher(exists=True, match=True, locked=True) as (w, _):
            assert w.state == "locked"

    def test_unlocked_when_content_matches_but_not_immutable(self):
        with _make_watcher(exists=True, match=True, locked=False) as (w, _):
            assert w.state == "unlocked"

    def test_overwritten_takes_priority_over_lock_check(self):
        # If content doesn't match, we don't even check the lock.
        with _make_watcher(exists=True, match=False, locked=True) as (w, _):
            assert w.state == "overwritten"


# ── Event paths ───────────────────────────────────────────────────────────────

class TestEventPaths:
    """
    Simulate incoming events by calling the internal callbacks directly.
    Each path should trigger _recheck() and update state accordingly.
    """

    def test_inotify_detects_steam_overwrite(self):
        """inotify fires for desktop_neptune.vdf → state becomes overwritten."""
        with _make_watcher(match=True, locked=True) as (w, _):
            assert w.state == "locked"

            with patch.object(scw, "_drain_inotify", return_value=["desktop_neptune.vdf"]), \
                 patch.object(scw, "_files_match", return_value=False):
                w._on_inotify(5, None)

            assert w.state == "overwritten"

    def test_inotify_ignores_unrelated_files(self):
        """inotify fires for a different file → state unchanged."""
        with _make_watcher(match=True, locked=True) as (w, _):
            with patch.object(scw, "_drain_inotify", return_value=["other.vdf"]):
                w._on_inotify(5, None)

            assert w.state == "locked"

    def test_inotify_detects_recovery_after_fix(self):
        """After fix-and-lock the copy triggers inotify → state becomes locked."""
        with _make_watcher(match=False) as (w, _):
            assert w.state == "overwritten"

            with patch.object(scw, "_drain_inotify", return_value=["desktop_neptune.vdf"]), \
                 patch.object(scw, "_files_match", return_value=True), \
                 patch.object(scw, "_is_locked",   return_value=True):
                w._on_inotify(5, None)

            assert w.state == "locked"

    def test_sentinel_detects_lock_applied(self):
        """Sentinel fires after chattr +i → state transitions unlocked → locked."""
        with _make_watcher(match=True, locked=False) as (w, _):
            assert w.state == "unlocked"

            with patch.object(scw, "_is_locked", return_value=True):
                w._on_sentinel_changed(None, None, None, None)

            assert w.state == "locked"

    def test_sentinel_detects_unlock(self):
        """Sentinel fires after chattr -i → state transitions locked → unlocked."""
        with _make_watcher(match=True, locked=True) as (w, _):
            assert w.state == "locked"

            with patch.object(scw, "_is_locked", return_value=False):
                w._on_sentinel_changed(None, None, None, None)

            assert w.state == "unlocked"

    def test_poll_detects_external_chattr(self):
        """Fallback poll catches external chattr changes inotify misses."""
        with _make_watcher(match=True, locked=True) as (w, _):
            assert w.state == "locked"

            with patch.object(scw, "_is_locked", return_value=False):
                result = w._on_poll()

            assert w.state == "unlocked"
            assert result is scw.GLib.SOURCE_CONTINUE  # timer keeps running

    def test_poll_detects_external_overwrite(self):
        """Fallback poll catches Steam overwriting while tray was busy."""
        with _make_watcher(match=True, locked=True) as (w, _):
            with patch.object(scw, "_files_match", return_value=False):
                w._on_poll()

            assert w.state == "overwritten"


# ── Terminal actions ──────────────────────────────────────────────────────────

class TestTerminalActions:
    """
    Terminal methods open a Konsole subprocess with a bash script.
    We mock subprocess.Popen and inspect the generated script content.
    """

    @patch.object(scw.subprocess, "Popen")
    def test_fix_and_lock_copies_then_chattr(self, mock_popen):
        """fix-and-lock script: cp source → target, then chattr +i, then touch sentinel."""
        with _make_watcher() as (w, _):
            w.open_fix_and_lock_terminal()

        script = mock_popen.call_args[0][0][-1]  # last arg of: distrobox-host-exec konsole --noclose -e bash -c <script>
        assert f"cp '{_SOURCE}' '{_TARGET}'" in script
        assert f"chattr +i '{_TARGET}'" in script
        assert f"touch '{_SENTINEL}'" in script

    @patch.object(scw.subprocess, "Popen")
    def test_fix_and_lock_does_not_unlock(self, mock_popen):
        """fix-and-lock must not run chattr -i."""
        with _make_watcher() as (w, _):
            w.open_fix_and_lock_terminal()

        script = mock_popen.call_args[0][0][-1]
        assert "chattr -i" not in script

    @patch.object(scw.subprocess, "Popen")
    def test_lock_only_no_copy(self, mock_popen):
        """lock-only script: chattr +i only, no cp (content already correct)."""
        with _make_watcher() as (w, _):
            w.open_lock_terminal()

        script = mock_popen.call_args[0][0][-1]
        assert f"chattr +i '{_TARGET}'" in script
        assert f"touch '{_SENTINEL}'" in script
        assert f"cp '{_SOURCE}'" not in script

    @patch.object(scw.subprocess, "Popen")
    def test_unlock_removes_lock_no_copy(self, mock_popen):
        """unlock script: chattr -i only, no cp, no chattr +i."""
        with _make_watcher() as (w, _):
            w.open_unlock_terminal()

        script = mock_popen.call_args[0][0][-1]
        assert f"chattr -i '{_TARGET}'" in script
        assert f"touch '{_SENTINEL}'" in script
        assert f"cp '{_SOURCE}'" not in script
        assert f"sudo chattr +i" not in script  # echo text mentions "chattr +i" for context, but no actual command

    @patch.object(scw.subprocess, "Popen")
    def test_all_terminals_use_distrobox_host_exec(self, mock_popen):
        """All terminal actions must go through distrobox-host-exec konsole."""
        with _make_watcher() as (w, _):
            for method in (w.open_lock_terminal,
                           w.open_fix_and_lock_terminal,
                           w.open_unlock_terminal):
                mock_popen.reset_mock()
                method()
                args = mock_popen.call_args[0][0]
                assert args[0] == "distrobox-host-exec"
                assert "konsole" in args


# ── Label property ────────────────────────────────────────────────────────────

class TestLabels:
    """Every state produces a non-empty, distinct label."""

    STATES = ["locked", "unlocked", "overwritten", "no_source"]

    def test_all_states_have_labels(self):
        with _make_watcher() as (w, _):
            labels = set()
            for state in self.STATES:
                w._state = state
                label = w.label
                assert label, f"empty label for state '{state}'"
                assert "Steam config" in label, f"label missing prefix for '{state}'"
                labels.add(label)
            assert len(labels) == len(self.STATES), "duplicate labels across states"
