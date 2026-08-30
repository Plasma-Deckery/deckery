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


# ── _version_label ────────────────────────────────────────────────────────────

class TestVersionLabel:
    """
    _version_label() formats the tray header string.
    Used both on first build and whenever the updater state changes.
    """

    def test_normal_version(self, tray_mod):
        assert tray_mod._version_label("0.1.8") == "Deckery v0.1.8"

    def test_unknown_version(self, tray_mod):
        # No tags in repo → show dev label without version suffix.
        assert tray_mod._version_label("unknown") == "Deckery (dev)"

    def test_semver_with_patch(self, tray_mod):
        assert tray_mod._version_label("1.2.34") == "Deckery v1.2.34"

    def test_empty_string_treated_as_version(self, tray_mod):
        # Edge case: empty string is not "unknown" → shows "Deckery v"
        assert tray_mod._version_label("") == "Deckery v"


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

    def test_warn_when_steam_active(self, tray_mod):
        # Steam Input still active → user needs to act → amber.
        import steam_bridge
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state=steam_bridge.SteamState.ACTIVE, has_update=False,
        ) == "warn"

    def test_ok_when_steam_ok(self, tray_mod):
        import steam_bridge
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state=steam_bridge.SteamState.OK, has_update=False,
        ) == "ok"

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

    def test_ok_when_steam_user_missing(self, tray_mod):
        # No Steam user logged in → no action needed → ok.
        import steam_bridge
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state=steam_bridge.SteamState.USER_MISSING, has_update=False,
        ) == "ok"

    def test_ok_when_steam_config_missing(self, tray_mod):
        # Configset file not found → ok (Steam Input already inactive).
        import steam_bridge
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state=steam_bridge.SteamState.CONFIG_MISSING, has_update=False,
        ) == "ok"

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

    def test_steam_active_loses_to_err(self, tray_mod):
        # Steam ACTIVE (warn) + service inactive (warn) → warn, not err.
        import steam_bridge
        assert tray_mod._tray_state(
            {"makima": "inactive"},
            paused=False, steam_state=steam_bridge.SteamState.ACTIVE, has_update=False,
        ) == "warn"

    def test_empty_statuses_is_ok(self, tray_mod):
        # No services monitored → nothing can be wrong.
        assert tray_mod._tray_state(
            {}, paused=False, steam_state="locked", has_update=False,
        ) == "ok"

    def test_err_when_no_device(self, tray_mod):
        # errors["no_device"] present → red, even if service is active.
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state="locked", has_update=False,
            no_device=True,
        ) == "err"

    def test_err_when_base_config_error(self, tray_mod):
        # errors["base_config"] present → red, even if service is active.
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state="locked", has_update=False,
            base_config_error=True,
        ) == "err"

    def test_base_config_error_beats_warn_and_update(self, tray_mod):
        # base_config_error + paused + update available → err wins.
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=True, steam_state="locked", has_update=True,
            base_config_error=True,
        ) == "err"

    def test_reinitializing_is_warn(self, tray_mod):
        # Lifecycle "reinitializing" → amber warning, not error.
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state="locked", has_update=False,
            reinitializing=True,
        ) == "warn"

    def test_base_config_error_beats_reinitializing(self, tray_mod):
        # base_config_error (err) wins over reinitializing (warn).
        assert tray_mod._tray_state(
            {"makima": "active"},
            paused=False, steam_state="locked", has_update=False,
            base_config_error=True, reinitializing=True,
        ) == "err"

