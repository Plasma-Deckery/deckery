"""
test_tray.py — Tests for pure state-routing functions in deckery-tray.py.

Covers:
  • _tray_state:         combined system state → icon priority key
  • _steam_item_state:   steam watcher state → dot colour + unlock sensitivity
  • _steam_click_action: steam watcher state → which terminal action to open

All three functions are GTK-free and can be called directly.

Loading strategy
────────────────
deckery-tray.py has a hyphen in its name so it cannot be imported with a
normal `import` statement.  We use importlib to load it under a unique
module name.  GTK dependencies (Gtk, GdkPixbuf, AyatanaAppIndicator3) are
already stubbed by conftest.py.  updater + steam_config_watcher are
temporarily replaced in sys.modules inside the `tray_mod` fixture so that
DeckeryTray.__init__ is never executed during import.
"""

import sys
import os
import importlib.util
from unittest.mock import MagicMock
import pytest

_TRAY_PATH = os.path.join(os.path.dirname(__file__), "..", "deckery-tray.py")


@pytest.fixture(scope="module")
def tray_mod():
    """
    Load deckery-tray.py with all external deps mocked.
    Yields the module so tests can access its pure functions.
    Restores sys.modules afterwards so other test files are unaffected.
    """
    # Save whatever is currently in sys.modules for these keys
    # (by the time this fixture runs, test_updater.py and
    #  test_steam_config_watcher.py have already been collected, so the
    #  real modules are present and will be restored after yield).
    _saved = {k: sys.modules.get(k) for k in ("updater", "steam_config_watcher")}
    sys.modules["updater"]              = MagicMock()
    sys.modules["steam_config_watcher"] = MagicMock()

    try:
        spec = importlib.util.spec_from_file_location("deckery_tray_tests", _TRAY_PATH)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod
    finally:
        for k, v in _saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


# ── _tray_state ───────────────────────────────────────────────────────────────

class TestTrayState:
    """
    _tray_state() maps combined system state to an icon priority key.
    Priority (highest first): 'err' > 'warn' > 'update' > 'ok'.
    """

    def test_ok_when_everything_fine(self, tray_mod):
        assert tray_mod._tray_state(
            {"makima": "active", "deckery-hud": "active"},
            paused=False, steam_state="locked", has_update=False,
        ) == "ok"

    def test_err_when_service_failed(self, tray_mod):
        assert tray_mod._tray_state(
            {"makima": "failed"},
            paused=False, steam_state="locked", has_update=False,
        ) == "err"

    def test_err_when_steam_overwritten(self, tray_mod):
        # Steam overwrote the config → critical, needs immediate action.
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state="overwritten", has_update=False,
        ) == "err"

    def test_warn_when_service_inactive(self, tray_mod):
        assert tray_mod._tray_state(
            {"makima": "inactive"},
            paused=False, steam_state="locked", has_update=False,
        ) == "warn"

    def test_warn_when_service_unknown(self, tray_mod):
        assert tray_mod._tray_state(
            {"makima": "unknown"},
            paused=False, steam_state="locked", has_update=False,
        ) == "warn"

    def test_warn_when_paused(self, tray_mod):
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=True, steam_state="locked", has_update=False,
        ) == "warn"

    def test_warn_when_steam_unlocked(self, tray_mod):
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state="unlocked", has_update=False,
        ) == "warn"

    def test_warn_when_steam_no_source(self, tray_mod):
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state="no_source", has_update=False,
        ) == "warn"

    def test_update_when_no_other_issues(self, tray_mod):
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state="locked", has_update=True,
        ) == "update"

    def test_err_beats_warn_and_update(self, tray_mod):
        # Service failed + steam unlocked + update available → err wins.
        assert tray_mod._tray_state(
            {"makima": "failed"},
            paused=True, steam_state="unlocked", has_update=True,
        ) == "err"

    def test_warn_beats_update(self, tray_mod):
        # Paused + update available → warn, not update.
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=True, steam_state="locked", has_update=True,
        ) == "warn"

    def test_steam_err_beats_warn(self, tray_mod):
        # overwritten (err) + service inactive (warn) → err.
        assert tray_mod._tray_state(
            {"makima": "inactive"},
            paused=False, steam_state="overwritten", has_update=False,
        ) == "err"

    def test_empty_statuses_is_ok(self, tray_mod):
        # No services monitored → nothing can be wrong.
        assert tray_mod._tray_state(
            {}, paused=False, steam_state="locked", has_update=False,
        ) == "ok"


# ── _steam_item_state ─────────────────────────────────────────────────────────

class TestSteamItemState:
    """
    _steam_item_state() returns (dot_key, unlock_sensitive) for each state.
    Unlock is only enabled when the file is actually locked (user can remove it).
    """

    def test_locked_green_unlock_enabled(self, tray_mod):
        dot, unlock = tray_mod._steam_item_state("locked")
        assert dot    == "ok"
        assert unlock is True

    def test_unlocked_yellow_unlock_disabled(self, tray_mod):
        # File is already unlocked — "Unlock" would do nothing.
        dot, unlock = tray_mod._steam_item_state("unlocked")
        assert dot    == "warn"
        assert unlock is False

    def test_overwritten_red_unlock_disabled(self, tray_mod):
        # File was overwritten — lock it again first before unlocking makes sense.
        dot, unlock = tray_mod._steam_item_state("overwritten")
        assert dot    == "err"
        assert unlock is False

    def test_no_source_yellow_unlock_disabled(self, tray_mod):
        dot, unlock = tray_mod._steam_item_state("no_source")
        assert dot    == "warn"
        assert unlock is False

    def test_unknown_state_grey_unlock_disabled(self, tray_mod):
        dot, unlock = tray_mod._steam_item_state("something_unexpected")
        assert dot    == "grey"
        assert unlock is False


# ── _steam_click_action ───────────────────────────────────────────────────────

class TestSteamClickAction:
    """
    _steam_click_action() routes a click on the steam status item to the
    correct terminal action, or None when clicking does nothing.
    """

    def test_overwritten_opens_fix_and_lock(self, tray_mod):
        assert tray_mod._steam_click_action("overwritten") == "fix_and_lock"

    def test_unlocked_opens_lock(self, tray_mod):
        assert tray_mod._steam_click_action("unlocked") == "lock"

    def test_locked_is_noop(self, tray_mod):
        # Already correct — nothing to do on click.
        assert tray_mod._steam_click_action("locked") is None

    def test_no_source_is_noop(self, tray_mod):
        # Source file missing — there's nothing to lock or fix.
        assert tray_mod._steam_click_action("no_source") is None
