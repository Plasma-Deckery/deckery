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
  • Packaged installs (#78): detection, labels, hint text, never launches get.sh

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
    """local_version() reads the tag of the checked-out commit, or 'unknown'.

    Deliberately not the highest tag in the repo — that was the behaviour
    80e8c3f fixed. Once tags have been fetched the highest one is present
    regardless of what is checked out, so a dev snapshot claimed to be a
    release. 'unknown' is what marks a checkout as being off-release.
    """

    def _git_result(self, stdout: str, returncode: int = 0):
        r = MagicMock()
        r.returncode = returncode
        r.stdout = stdout
        return r

    def test_queries_head_exactly(self):
        """Guards 80e8c3f: the tag must come from HEAD, not from a tag listing."""
        with patch.object(upd.subprocess, "run",
                          return_value=self._git_result("v0.1.6\n")) as run:
            assert local_version() == "0.1.6"
        argv = run.call_args[0][0]
        assert "describe" in argv
        assert "--exact-match" in argv
        assert "HEAD" in argv

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

    def test_unknown_local_version_ahead_of_release(self):
        # "unknown" means HEAD sits on no tag — a dev checkout. Newer than the
        # latest tag, so the offer is a rollback, not an update.
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag",        return_value="0.2.0"), \
             patch.object(upd, "local_version",            return_value="unknown"), \
             patch.object(upd, "_local_commit_timestamp",  return_value=2000), \
             patch.object(upd, "_tag_commit_timestamp",    return_value=1000):
            u._check_thread()
        assert u._state == UpdateState.AHEAD_OF_RELEASE

    def test_unknown_local_version_behind_release(self):
        # Same "unknown", but older than the tag — a partial or stale checkout.
        # Here the release genuinely is an update.
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag",        return_value="0.2.0"), \
             patch.object(upd, "local_version",            return_value="unknown"), \
             patch.object(upd, "_local_commit_timestamp",  return_value=1000), \
             patch.object(upd, "_tag_commit_timestamp",    return_value=2000):
            u._check_thread()
        assert u._state == UpdateState.UPDATE_AVAILABLE

    def test_unknown_local_version_without_timestamps(self):
        # No timestamps obtainable → cannot prove we are ahead, so offer the
        # release rather than silently claiming to be current.
        u = self._make()
        with patch.object(upd, "_fetch_latest_tag",        return_value="0.2.0"), \
             patch.object(upd, "local_version",            return_value="unknown"), \
             patch.object(upd, "_local_commit_timestamp",  return_value=None), \
             patch.object(upd, "_tag_commit_timestamp",    return_value=None):
            u._check_thread()
        assert u._state == UpdateState.UPDATE_AVAILABLE

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


# ── Packaged installs (Issue #78) ─────────────────────────────────────────────

class TestInGitCheckout:
    """_in_git_checkout finds .git in the path or any parent."""

    def test_clone_parent(self, tmp_path):
        (tmp_path / ".git").mkdir()
        sub = tmp_path / "tray"
        sub.mkdir()
        assert upd._in_git_checkout(str(sub))

    def test_worktree_git_file(self, tmp_path):
        (tmp_path / ".git").write_text("gitdir: /elsewhere\n")
        sub = tmp_path / "tray"
        sub.mkdir()
        assert upd._in_git_checkout(str(sub))

    def test_no_git_anywhere(self, tmp_path):
        sub = tmp_path / "usr" / "lib" / "deckery" / "tray"
        sub.mkdir(parents=True)
        # tmp_path lives under /tmp, which has no .git above it.
        assert not upd._in_git_checkout(str(sub))


class TestIsPackagedInstall:
    """is_packaged_install: no git checkout around the tray AND the tray file
    is owned by an RPM."""

    @pytest.fixture(autouse=True)
    def _reset_cache(self, monkeypatch):
        monkeypatch.setattr(upd, "_packaged", None)

    def _rpm(self, stdout="0.5.0", returncode=0):
        r = MagicMock()
        r.returncode = returncode
        r.stdout = stdout
        return r

    def test_rpm_owned_without_git_is_packaged(self, monkeypatch):
        monkeypatch.setattr(upd, "_in_git_checkout", lambda p: False)
        with patch.object(upd.subprocess, "run", return_value=self._rpm()) as run:
            assert upd.is_packaged_install()
        argv = run.call_args[0][0]
        assert argv[:2] == ["rpm", "-qf"]
        assert argv[-1] == upd._THIS_FILE

    def test_git_checkout_is_source_and_never_asks_rpm(self, monkeypatch):
        monkeypatch.setattr(upd, "_in_git_checkout", lambda p: True)
        with patch.object(upd.subprocess, "run") as run:
            assert not upd.is_packaged_install()
        run.assert_not_called()

    def test_not_owned_by_any_package_is_source(self, monkeypatch):
        monkeypatch.setattr(upd, "_in_git_checkout", lambda p: False)
        not_owned = self._rpm(stdout="file /x is not owned by any package\n", returncode=1)
        with patch.object(upd.subprocess, "run", return_value=not_owned):
            assert not upd.is_packaged_install()

    def test_no_rpm_binary_is_source(self, monkeypatch):
        monkeypatch.setattr(upd, "_in_git_checkout", lambda p: False)
        with patch.object(upd.subprocess, "run", side_effect=FileNotFoundError):
            assert not upd.is_packaged_install()

    def test_result_is_cached(self, monkeypatch):
        monkeypatch.setattr(upd, "_in_git_checkout", lambda p: False)
        with patch.object(upd.subprocess, "run", return_value=self._rpm()) as run:
            upd.is_packaged_install()
            upd.is_packaged_install()
        assert run.call_count == 1

    def test_this_test_checkout_is_source(self, monkeypatch):
        # The test suite runs from a git checkout: the real detection must say
        # "source", which is what every other Updater test relies on.
        assert not upd.is_packaged_install()

    def test_updater_uses_detection_by_default(self, monkeypatch):
        monkeypatch.setattr(upd, "is_packaged_install", lambda: True)
        assert Updater(on_state_change=MagicMock()).packaged


class TestLocalVersionPackageOwner:
    """Without the deckery meta-package, the version of the package owning the
    tray (deckery-tray) is used."""

    def test_falls_back_to_owning_package(self):
        def run(argv, **kw):
            r = MagicMock()
            if argv[:2] == ["rpm", "-qf"]:
                r.returncode, r.stdout = 0, "0.5.0"
            else:
                r.returncode, r.stdout = 1, ""
            return r
        with patch.object(upd.subprocess, "run", side_effect=run):
            assert local_version() == "0.5.0"


class TestPackagedMode:
    """On packaged installs the tray only reports; it never installs."""

    def _make(self, state=UpdateState.UPDATE_AVAILABLE, latest="0.6.0") -> Updater:
        u = Updater(on_state_change=MagicMock(), packaged=True)
        u._state = state
        u._latest = latest
        return u

    @pytest.mark.parametrize("state", list(UpdateState))
    def test_click_never_launches_anything(self, state):
        u = self._make(state=state)
        with patch.object(upd.subprocess, "Popen") as popen, \
             patch.object(upd.threading, "Thread"):
            u.on_clicked()
        popen.assert_not_called()

    def test_run_update_refuses(self):
        # Defence in depth: even a direct call must not start get.sh.
        u = self._make()
        with patch.object(upd.subprocess, "Popen") as popen:
            u._run_update()
        popen.assert_not_called()

    def test_update_available_label(self):
        u = self._make()
        assert u.label == "New version v0.6.0 — arrives with a system update"
        assert "Install" not in u.label
        assert u.sensitive

    @pytest.mark.parametrize("state", [UpdateState.IDLE, UpdateState.CHECKING,
                                       UpdateState.UP_TO_DATE, UpdateState.ERROR])
    def test_other_labels_match_source_install(self, state):
        packaged = self._make(state=state)
        source = Updater(on_state_change=MagicMock(), packaged=False)
        source._state, source._latest = state, "0.6.0"
        assert packaged.label == source.label

    def test_up_to_date_click_rechecks(self):
        u = self._make(state=UpdateState.UP_TO_DATE)
        with patch.object(u, "_start_check") as start:
            u.on_clicked()
        start.assert_called_once()

    def test_update_available_keeps_auto_checking(self):
        # Sticky state from #78: on packaged installs a newer tag must still
        # be picked up while UPDATE_AVAILABLE is shown.
        u = self._make()
        with patch.object(u, "_start_check") as start:
            u._auto_check()
        start.assert_called_once()

    def test_source_update_available_stops_auto_checking(self):
        u = Updater(on_state_change=MagicMock(), packaged=False)
        u._state = UpdateState.UPDATE_AVAILABLE
        with patch.object(u, "_start_check") as start:
            u._auto_check()
        start.assert_not_called()

    def test_unknown_local_version_is_not_an_update(self):
        u = self._make(state=UpdateState.IDLE, latest=None)
        with patch.object(upd, "_fetch_latest_tag", return_value="0.6.0"), \
             patch.object(upd, "local_version",      return_value="unknown"):
            u._check_thread()
        assert u.state == UpdateState.ERROR

    def test_newer_tag_is_update_available(self):
        u = self._make(state=UpdateState.IDLE, latest=None)
        with patch.object(upd, "_fetch_latest_tag", return_value="0.6.0"), \
             patch.object(upd, "local_version",      return_value="0.5.0"):
            u._check_thread()
        assert u.state == UpdateState.UPDATE_AVAILABLE
        assert u.latest == "0.6.0"


class TestPackagedHintText:
    """Explanation text: plain words, no promise that it is installable now."""

    JARGON = ("rpm", "copr", "ostree", "layered", "package", "distrobox",
              "terminal", "ujust", "get.sh")

    def test_mentions_version(self):
        assert "v0.6.0" in upd.packaged_hint_text("0.6.0")

    def test_without_version(self):
        text = upd.packaged_hint_text(None)
        assert text and "vNone" not in text

    @pytest.mark.parametrize("latest", ["0.6.0", None])
    def test_no_jargon(self, latest):
        text = (upd.PACKAGED_HINT_TITLE + " " + upd.packaged_hint_text(latest)).lower()
        for word in self.JARGON:
            assert word not in text, word

    def test_does_not_promise_immediate_availability(self):
        text = upd.packaged_hint_text("0.6.0")
        assert "may not be available right away" in text
