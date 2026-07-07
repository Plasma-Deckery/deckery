"""
test_updater.py — Tests for updater.py.

Covers:
  • _parse_version: string → comparable tuple, including edge cases
  • local_version: reads highest git tag, handles missing tags and errors
  • _fetch_latest_tag: parses GitHub /tags API, picks highest semver
  • Updater._check_thread: UP_TO_DATE / UPDATE_AVAILABLE / ERROR routing
  • Updater.on_clicked: dispatches to _start_check or _run_update by state
  • Updater._auto_check: only checks when idle, always reschedules
  • Updater._run_update: Popen receives distrobox-host-exec + get.sh
  • Updater.label: correct text for every UpdateState
  • Updater.sensitive: clickable only in the right states

GLib is mocked in conftest.py — GLib.timeout_add_seconds in Updater.__init__
is captured but never executed, so no timer fires during tests.
"""

import json
import sys
import os
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import updater as upd
from updater import Updater, UpdateState, local_version, _parse_version, _fetch_latest_tag


# ── _parse_version ────────────────────────────────────────────────────────────

class TestParseVersion:
    """_parse_version converts a version string to a comparable int tuple."""

    def test_standard_version(self):
        assert _parse_version("0.1.5") == (0, 1, 5)

    def test_major_version(self):
        assert _parse_version("1.0.0") == (1, 0, 0)

    def test_numeric_ordering_not_lexicographic(self):
        # "0.1.10" > "0.1.9" numerically — lexicographic comparison would fail this.
        assert _parse_version("0.1.10") > _parse_version("0.1.9")

    def test_unknown_string_returns_fallback(self):
        assert _parse_version("unknown") == (0,)

    def test_empty_string_returns_fallback(self):
        assert _parse_version("") == (0,)

    def test_non_numeric_segment_returns_fallback(self):
        assert _parse_version("0.1.x") == (0,)

    def test_equal_versions(self):
        assert _parse_version("0.1.6") == _parse_version("0.1.6")

    def test_newer_local_is_greater(self):
        assert _parse_version("0.2.0") > _parse_version("0.1.9")


# ── local_version ─────────────────────────────────────────────────────────────

class TestLocalVersion:
    """local_version() reads the highest semver tag from git."""

    def _git_result(self, stdout: str, returncode: int = 0):
        r = MagicMock()
        r.returncode = returncode
        r.stdout = stdout
        return r

    def test_returns_highest_tag(self):
        with patch.object(upd.subprocess, "run",
                          return_value=self._git_result("v0.1.6\nv0.1.5\n")):
            assert local_version() == "0.1.6"

    def test_strips_leading_v(self):
        with patch.object(upd.subprocess, "run",
                          return_value=self._git_result("v1.2.3\n")):
            assert local_version() == "1.2.3"

    def test_no_tags_returns_unknown(self):
        with patch.object(upd.subprocess, "run",
                          return_value=self._git_result("", returncode=0)):
            assert local_version() == "unknown"

    def test_git_failure_returns_unknown(self):
        with patch.object(upd.subprocess, "run",
                          return_value=self._git_result("", returncode=128)):
            assert local_version() == "unknown"

    def test_git_not_found_returns_unknown(self):
        with patch.object(upd.subprocess, "run", side_effect=FileNotFoundError):
            assert local_version() == "unknown"

    def test_timeout_returns_unknown(self):
        with patch.object(upd.subprocess, "run", side_effect=TimeoutError):
            assert local_version() == "unknown"


# ── Updater.label ─────────────────────────────────────────────────────────────

class TestUpdaterLabel:
    """Updater.label returns the correct menu text for each state."""

    def _make(self) -> Updater:
        return Updater(on_state_change=MagicMock())

    def test_idle(self):
        u = self._make()
        u._state = UpdateState.IDLE
        assert "Update" in u.label

    def test_checking(self):
        u = self._make()
        u._state = UpdateState.CHECKING
        assert u.label  # non-empty
        assert "check" in u.label.lower() or "updat" in u.label.lower()

    def test_up_to_date(self):
        u = self._make()
        u._state = UpdateState.UP_TO_DATE
        assert u.label

    def test_update_available_includes_version(self):
        u = self._make()
        u._state  = UpdateState.UPDATE_AVAILABLE
        u._latest = "0.2.0"
        assert "0.2.0" in u.label

    def test_update_available_includes_install_cue(self):
        u = self._make()
        u._state  = UpdateState.UPDATE_AVAILABLE
        u._latest = "0.2.0"
        # User should see an action word so they know it's clickable.
        assert any(word in u.label for word in ("Install", "install", "Update", "update"))

    def test_error(self):
        u = self._make()
        u._state = UpdateState.ERROR
        assert u.label


# ── Updater.sensitive ─────────────────────────────────────────────────────────

class TestUpdaterSensitive:
    """Updater.sensitive controls whether the menu item is clickable."""

    def _make(self) -> Updater:
        return Updater(on_state_change=MagicMock())

    def test_checking_is_not_sensitive(self):
        u = self._make()
        u._state = UpdateState.CHECKING
        assert not u.sensitive

    def test_idle_is_sensitive(self):
        u = self._make()
        u._state = UpdateState.IDLE
        assert u.sensitive

    def test_update_available_is_sensitive(self):
        u = self._make()
        u._state = UpdateState.UPDATE_AVAILABLE
        assert u.sensitive

    def test_error_is_sensitive(self):
        # User can click to retry.
        u = self._make()
        u._state = UpdateState.ERROR
        assert u.sensitive

    def test_up_to_date_is_sensitive(self):
        # User can click to recheck manually.
        u = self._make()
        u._state = UpdateState.UP_TO_DATE
        assert u.sensitive


# ── _fetch_latest_tag ─────────────────────────────────────────────────────────

class TestFetchLatestTag:
    """_fetch_latest_tag fetches and parses the GitHub /tags API."""

    def _urlopen(self, tags: list[dict]):
        """Return a mock context manager whose .read() returns JSON tag data."""
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__  = MagicMock(return_value=False)
        cm.read      = MagicMock(return_value=json.dumps(tags).encode())
        return cm

    def test_returns_highest_semver(self):
        tags = [{"name": "v0.1.5"}, {"name": "v0.2.0"}, {"name": "v0.1.9"}]
        with patch.object(upd.urllib.request, "urlopen", return_value=self._urlopen(tags)):
            assert _fetch_latest_tag() == "0.2.0"

    def test_strips_v_prefix(self):
        tags = [{"name": "v1.2.3"}]
        with patch.object(upd.urllib.request, "urlopen", return_value=self._urlopen(tags)):
            assert _fetch_latest_tag() == "1.2.3"

    def test_numeric_sort_not_lexicographic(self):
        # "0.1.10" must beat "0.1.9"; lexicographic comparison would return "0.1.9".
        tags = [{"name": "v0.1.9"}, {"name": "v0.1.10"}]
        with patch.object(upd.urllib.request, "urlopen", return_value=self._urlopen(tags)):
            assert _fetch_latest_tag() == "0.1.10"

    def test_skips_non_semver_tags(self):
        tags = [{"name": "nightly"}, {"name": "v0.1.0"}]
        with patch.object(upd.urllib.request, "urlopen", return_value=self._urlopen(tags)):
            assert _fetch_latest_tag() == "0.1.0"

    def test_no_valid_tags_raises_value_error(self):
        tags = [{"name": "nightly"}, {"name": "beta"}]
        with patch.object(upd.urllib.request, "urlopen", return_value=self._urlopen(tags)):
            with pytest.raises(ValueError):
                _fetch_latest_tag()

    def test_empty_tag_list_raises_value_error(self):
        with patch.object(upd.urllib.request, "urlopen", return_value=self._urlopen([])):
            with pytest.raises(ValueError):
                _fetch_latest_tag()


# ── Updater._check_thread ─────────────────────────────────────────────────────

class TestCheckThread:
    """
    _check_thread() is the background worker that compares versions.
    Called synchronously here (no daemon thread) so assertions are immediate.
    """

    def _make(self) -> Updater:
        return Updater(on_state_change=MagicMock())

    def test_up_to_date_when_versions_equal(self):
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag", return_value="0.1.5"), \
             patch.object(upd, "local_version",      return_value="0.1.5"):
            u._check_thread()
        assert u._state == UpdateState.UP_TO_DATE

    def test_up_to_date_when_local_is_newer(self):
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag", return_value="0.1.5"), \
             patch.object(upd, "local_version",      return_value="0.2.0"):
            u._check_thread()
        assert u._state == UpdateState.UP_TO_DATE

    def test_update_available_when_remote_is_newer(self):
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag", return_value="0.2.0"), \
             patch.object(upd, "local_version",      return_value="0.1.5"):
            u._check_thread()
        assert u._state  == UpdateState.UPDATE_AVAILABLE
        assert u._latest == "0.2.0"

    def test_up_to_date_when_local_version_unknown(self):
        # Can't tell if update is needed → treat as up to date (safe default).
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag", return_value="0.2.0"), \
             patch.object(upd, "local_version",      return_value="unknown"):
            u._check_thread()
        assert u._state == UpdateState.UP_TO_DATE

    def test_error_when_network_fails(self):
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag", side_effect=OSError("timeout")):
            u._check_thread()
        assert u._state == UpdateState.ERROR

    def test_error_when_json_malformed(self):
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag", side_effect=ValueError("no tags")):
            u._check_thread()
        assert u._state == UpdateState.ERROR


# ── Updater.on_clicked ────────────────────────────────────────────────────────

class TestOnClicked:
    """on_clicked() routes to _start_check or _run_update depending on state."""

    def _make(self) -> Updater:
        return Updater(on_state_change=MagicMock())

    def test_idle_starts_check(self):
        u = self._make()
        u._state = UpdateState.IDLE
        with patch.object(u, "_start_check") as mock_start:
            u.on_clicked()
        mock_start.assert_called_once()

    def test_up_to_date_starts_check(self):
        u = self._make()
        u._state = UpdateState.UP_TO_DATE
        with patch.object(u, "_start_check") as mock_start:
            u.on_clicked()
        mock_start.assert_called_once()

    def test_error_starts_check(self):
        u = self._make()
        u._state = UpdateState.ERROR
        with patch.object(u, "_start_check") as mock_start:
            u.on_clicked()
        mock_start.assert_called_once()

    def test_update_available_runs_update(self):
        u = self._make()
        u._state = UpdateState.UPDATE_AVAILABLE
        with patch.object(u, "_run_update") as mock_run:
            u.on_clicked()
        mock_run.assert_called_once()

    def test_checking_does_nothing(self):
        u = self._make()
        u._state = UpdateState.CHECKING
        with patch.object(u, "_start_check") as mock_start, \
             patch.object(u, "_run_update")  as mock_run:
            u.on_clicked()
        mock_start.assert_not_called()
        mock_run.assert_not_called()


# ── Updater._auto_check ───────────────────────────────────────────────────────

class TestAutoCheck:
    """_auto_check() fires from the GLib timer; checks when idle, always reschedules."""

    def _make(self) -> Updater:
        return Updater(on_state_change=MagicMock())

    def test_starts_check_when_idle(self):
        u = self._make()
        u._state = UpdateState.IDLE
        with patch.object(u, "_start_check") as mock_start:
            u._auto_check()
        mock_start.assert_called_once()

    def test_starts_check_when_up_to_date(self):
        u = self._make()
        u._state = UpdateState.UP_TO_DATE
        with patch.object(u, "_start_check") as mock_start:
            u._auto_check()
        mock_start.assert_called_once()

    def test_starts_check_when_error(self):
        u = self._make()
        u._state = UpdateState.ERROR
        with patch.object(u, "_start_check") as mock_start:
            u._auto_check()
        mock_start.assert_called_once()

    def test_no_check_when_already_checking(self):
        u = self._make()
        u._state = UpdateState.CHECKING
        with patch.object(u, "_start_check") as mock_start:
            u._auto_check()
        mock_start.assert_not_called()

    def test_reschedules_hourly_timer(self):
        u = self._make()
        upd.GLib.timeout_add_seconds.reset_mock()
        with patch.object(u, "_start_check"):
            u._auto_check()
        upd.GLib.timeout_add_seconds.assert_called_with(u.CHECK_INTERVAL_S, u._auto_check)

    def test_returns_source_remove(self):
        u = self._make()
        with patch.object(u, "_start_check"):
            result = u._auto_check()
        assert result is upd.GLib.SOURCE_REMOVE


# ── Updater._run_update ───────────────────────────────────────────────────────

class TestRunUpdate:
    """_run_update() opens a distrobox-host-exec konsole running get.sh."""

    def _make(self) -> Updater:
        return Updater(on_state_change=MagicMock())

    def test_uses_distrobox_host_exec(self):
        u = self._make()
        with patch.object(upd.subprocess, "Popen") as mock_popen:
            u._run_update()
        args = mock_popen.call_args[0][0]
        assert args[0] == "distrobox-host-exec"
        assert "konsole" in args

    def test_passes_get_sh_path(self):
        u = self._make()
        with patch.object(upd.subprocess, "Popen") as mock_popen:
            u._run_update()
        args = mock_popen.call_args[0][0]
        assert upd._GET_SH in args
