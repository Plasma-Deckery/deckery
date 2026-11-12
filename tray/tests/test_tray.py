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



# ── _makima_state ─────────────────────────────────────────────────────────────

class TestMakimaStateConfigs:
    """Everything the submenu needs has to survive the read of state.json."""

    def _state(self, tray_mod, tmp_path, monkeypatch, document):
        import json
        path = tmp_path / "makima-state.json"
        path.write_text(json.dumps(document))
        monkeypatch.setattr(tray_mod, "_STATE_JSON", str(path))
        return tray_mod._makima_state()

    def test_exclusive_group_reaches_the_submenu(self, tray_mod, tmp_path, monkeypatch):
        # Dropping this field once made every group render as loose checkboxes:
        # display_rows() reads it, and absent means "not in a group".
        state = self._state(tray_mod, tmp_path, monkeypatch, {
            "lifecycle": "ready",
            "configs": [{"name": "KDE Desktop Layout Grid", "kind": "module",
                         "exclusive_group": "kde-desktop-layout", "enabled": False}],
        })
        assert state.configs[0]["exclusive_group"] == "kde-desktop-layout"

    def test_a_config_without_a_group_reports_none(self, tray_mod, tmp_path, monkeypatch):
        state = self._state(tray_mod, tmp_path, monkeypatch, {
            "lifecycle": "ready",
            "configs": [{"name": "Voice Control", "kind": "module", "enabled": True}],
        })
        assert state.configs[0]["exclusive_group"] is None

    def test_config_roots_are_passed_through(self, tray_mod, tmp_path, monkeypatch):
        state = self._state(tray_mod, tmp_path, monkeypatch, {
            "lifecycle": "ready", "configs": [],
            "config_roots": {"system": "/usr/share/deckery/configs",
                             "user":   "/home/u/.config/deckery"},
        })
        assert state.config_roots["system"] == "/usr/share/deckery/configs"

    def test_missing_config_roots_are_an_empty_mapping(self, tray_mod, tmp_path, monkeypatch):
        # An older makima, or one that has not finished starting. The submenu
        # falls back to the assumed user path and hides the shipped folder.
        state = self._state(tray_mod, tmp_path, monkeypatch, {
            "lifecycle": "starting", "configs": [], "config_roots": None,
        })
        assert state.config_roots == {}

    def test_an_absent_state_file_yields_empty_roots(self, tray_mod, tmp_path, monkeypatch):
        monkeypatch.setattr(tray_mod, "_STATE_JSON", str(tmp_path / "gone.json"))
        assert tray_mod._makima_state().config_roots == {}


# ── Global error text ─────────────────────────────────────────────────────────

class TestMakimaErrorText:
    """makima writes a message behind "no device"; the tray has to carry it."""

    def _state(self, tray_mod, tmp_path, monkeypatch, document):
        import json
        path = tmp_path / "makima-state.json"
        path.write_text(json.dumps(document))
        monkeypatch.setattr(tray_mod, "_STATE_JSON", str(path))
        return tray_mod._makima_state()

    def test_the_no_device_message_is_carried_through(self, tray_mod, tmp_path, monkeypatch):
        # The two words in the status row cannot say to check [device] names.
        state = self._state(tray_mod, tmp_path, monkeypatch, {
            "lifecycle": "ready", "configs": [],
            "errors": {"no_device": {"severity": "error",
                                     "message": "check that [device] names matches evtest"}},
        })
        assert state.no_device
        assert "evtest" in state.error_text

    def test_both_global_errors_are_shown_together(self, tray_mod, tmp_path, monkeypatch):
        # Showing only the first would hide the one the user can act on.
        state = self._state(tray_mod, tmp_path, monkeypatch, {
            "lifecycle": "ready", "configs": [],
            "errors": {"no_device":   {"severity": "error", "message": "no hardware"},
                       "base_config": {"severity": "error", "message": "line 4: bad"}},
        })
        assert "no hardware" in state.error_text
        assert "line 4: bad" in state.error_text

    def test_a_healthy_makima_has_nothing_to_report(self, tray_mod, tmp_path, monkeypatch):
        state = self._state(tray_mod, tmp_path, monkeypatch, {
            "lifecycle": "ready", "configs": [], "errors": {},
        })
        assert state.error_text == ""

    def test_an_error_without_a_message_does_not_offer_details(self, tray_mod, tmp_path, monkeypatch):
        # An older makima, or one that set the flag and no text. Inviting a
        # click that opens an empty dialog is worse than not inviting it.
        state = self._state(tray_mod, tmp_path, monkeypatch, {
            "lifecycle": "ready", "configs": [],
            "errors": {"no_device": {"severity": "error"}},
        })
        assert state.no_device
        assert state.error_text == ""

    def test_the_row_only_invites_a_click_when_there_is_something_behind_it(self, tray_mod):
        assert tray_mod._with_details("no device", "why") == "no device — click for details"
        assert tray_mod._with_details("no device", "") == "no device"


class TestStateReader:
    """One module opens makima's state file; both sides go through it."""

    def test_a_missing_file_is_not_an_error(self, tmp_path):
        import state
        assert state.read(str(tmp_path / "gone.json")) == {}

    def test_unreadable_content_yields_nothing_rather_than_raising(self, tmp_path):
        # A truncated write, caught mid-rename. The tray polls twice a second;
        # taking it down over one bad read would be the wrong trade.
        import state
        p = tmp_path / "makima-state.json"
        p.write_text('{"lifecycle": "rea')
        assert state.read(str(p)) == {}

    def test_config_roots_come_from_makima_when_it_has_spoken(self, tmp_path):
        import json, state
        p = tmp_path / "makima-state.json"
        p.write_text(json.dumps({"config_roots": {"system": "/usr/share/deckery/configs",
                                                  "user": "/home/u/.config/deckery"}}))
        assert state.config_roots(str(p)) == ["/usr/share/deckery/configs",
                                              "/home/u/.config/deckery"]

    def test_config_roots_fall_back_before_makima_has_ever_run(self, tmp_path):
        # Precisely when the setup wizard is on screen.
        import state
        roots = state.config_roots(str(tmp_path / "gone.json"))
        assert len(roots) == 2
        assert roots[1] == state.USER_CONFIGS

    def test_half_an_answer_is_not_used(self, tmp_path):
        # An older makima, or one still starting. Pairing a real system root
        # with a missing user root would send the wizard to the wrong place.
        import json, state
        p = tmp_path / "makima-state.json"
        p.write_text(json.dumps({"config_roots": {"system": "/usr/share/deckery/configs"}}))
        assert state.config_roots(str(p))[1] == state.USER_CONFIGS


class TestMalformedState:
    """The state file sits in /tmp, mode 1777. Its shape is not ours to assume.

    Before this, one field of the wrong type raised inside _makima_state(),
    landed in the outer except and returned _no_makima_state() — so the whole
    Controller Bindings submenu vanished and makima read as not running.
    """

    def _state(self, tray_mod, tmp_path, monkeypatch, document):
        import json
        path = tmp_path / "makima-state.json"
        path.write_text(json.dumps(document))
        monkeypatch.setattr(tray_mod, "_STATE_JSON", str(path))
        return tray_mod._makima_state()

    def _doc(self, **over):
        doc = {"lifecycle": "ready", "errors": {}, "configs": [
            {"name": "KDE Desktop", "kind": "module", "enabled": True,
             "status": "ok", "errors": []}]}
        doc.update(over)
        return doc

    def test_an_error_entry_of_the_wrong_shape_keeps_the_config_list(
            self, tray_mod, tmp_path, monkeypatch):
        s = self._state(tray_mod, tmp_path, monkeypatch,
                        self._doc(errors={"no_device": "a string"}))
        assert len(s.configs) == 1
        assert s.lifecycle == "ready"
        # The flag comes from the key being there; only the text is unusable.
        assert s.no_device
        assert s.error_text == ""

    def test_errors_itself_may_be_the_wrong_shape(
            self, tray_mod, tmp_path, monkeypatch):
        s = self._state(tray_mod, tmp_path, monkeypatch, self._doc(errors=["nope"]))
        assert len(s.configs) == 1
        assert not s.no_device

    def test_one_bad_config_entry_does_not_take_the_others(
            self, tray_mod, tmp_path, monkeypatch):
        doc = self._doc()
        doc["configs"].append("not a config")
        s = self._state(tray_mod, tmp_path, monkeypatch, doc)
        assert [c["name"] for c in s.configs] == ["KDE Desktop"]

    def test_context_of_the_wrong_shape_is_ignored(
            self, tray_mod, tmp_path, monkeypatch):
        s = self._state(tray_mod, tmp_path, monkeypatch, self._doc(context="nope"))
        assert len(s.configs) == 1
        assert s.paused is False

    def test_lifecycle_is_always_a_string(
            self, tray_mod, tmp_path, monkeypatch):
        # It is compared against "starting"/"reinitializing" downstream.
        s = self._state(tray_mod, tmp_path, monkeypatch, self._doc(lifecycle=7))
        assert s.lifecycle == ""

    def test_a_state_file_that_is_not_an_object_reads_as_absent(self, tmp_path):
        import state
        for raw in ("null", "[]", '"text"', "123"):
            p = tmp_path / "s.json"
            p.write_text(raw)
            assert state.read(str(p)) == {}
            assert len(state.config_roots(str(p))) == 2

    def test_config_roots_of_the_wrong_shape_fall_back(self, tmp_path):
        import json, state
        p = tmp_path / "s.json"
        p.write_text(json.dumps({"config_roots": "nope"}))
        assert state.config_roots(str(p))[1] == state.USER_CONFIGS


class TestStatePath:
    """One path, derived the same way makima derives it."""

    def test_the_state_file_lives_in_the_runtime_directory(self):
        import state
        assert state.STATE_JSON.endswith("/makima-state.json")
        assert "/tmp/" not in state.STATE_JSON, \
            "/tmp is mode 1777 — the state file must not land there"

    def test_it_is_the_same_directory_as_the_control_socket(self, tray_mod):
        import os, state
        assert os.path.dirname(state.STATE_JSON) == os.path.dirname(tray_mod._MAKIMA_SOCK)


# ── Update item on packaged installs (Issue #78) ──────────────────────────────

class TestPackagedUpdateClick:
    """On a packaged install the update item opens the explanation dialog;
    "Update now" (only where the system can run it) starts the system update
    through the updater, never get.sh."""

    def _fake_self(self, tray_mod, packaged=True, state="UPDATE_AVAILABLE",
                   command=("konsole",)):
        from types import SimpleNamespace
        fake = MagicMock()
        fake._updater.packaged = packaged
        fake._updater.state = getattr(tray_mod.UpdateState, state)
        fake._updater.latest = "0.6.0"
        fake._updater.system_update_command = list(command) if command else None
        fake._updater.hint = SimpleNamespace(title="Title", text="Text")
        return fake

    @pytest.fixture
    def dialog_cls(self, tray_mod, monkeypatch):
        cls = MagicMock()
        monkeypatch.setattr(tray_mod.Gtk, "MessageDialog", cls)
        return cls

    @pytest.mark.parametrize("state", ["UPDATE_AVAILABLE", "RESTART_REQUIRED"])
    def test_packaged_click_shows_hint_only(self, tray_mod, monkeypatch, state):
        fake = self._fake_self(tray_mod, state=state)
        popen = MagicMock()
        monkeypatch.setattr(tray_mod.subprocess, "Popen", popen)
        tray_mod.DeckeryTray._on_update_clicked(fake, None)
        fake._show_system_update_hint.assert_called_once()
        fake._updater.on_clicked.assert_not_called()
        fake._confirm_install.assert_not_called()
        popen.assert_not_called()

    def test_source_install_still_goes_to_updater(self, tray_mod, monkeypatch):
        fake = self._fake_self(tray_mod, packaged=False)
        monkeypatch.setattr(tray_mod, "_git_dirty_files", lambda d: [])
        tray_mod.DeckeryTray._on_update_clicked(fake, None)
        fake._show_system_update_hint.assert_not_called()
        fake._updater.on_clicked.assert_called_once()

    def test_update_now_button_starts_system_update(self, tray_mod, dialog_cls, monkeypatch):
        fake = self._fake_self(tray_mod)
        dialog = dialog_cls.return_value
        dialog.run.return_value = tray_mod.Gtk.ResponseType.OK
        monkeypatch.setattr(tray_mod, "UPDATE_NOW_BUTTON", "Update now")
        monkeypatch.setattr(tray_mod, "LATER_BUTTON", "Later")
        tray_mod.DeckeryTray._show_system_update_hint(fake)
        kw = dialog_cls.call_args.kwargs
        assert kw["text"] == "Title"
        assert kw["buttons"] == tray_mod.Gtk.ButtonsType.NONE
        dialog.format_secondary_text.assert_called_once_with("Text")
        labels = [c.args[0] for c in dialog.add_button.call_args_list]
        assert labels == ["Later", "Update now"]
        fake._updater.start_system_update.assert_called_once()
        dialog.destroy.assert_called_once()

    def test_later_does_nothing(self, tray_mod, dialog_cls):
        fake = self._fake_self(tray_mod)
        dialog_cls.return_value.run.return_value = tray_mod.Gtk.ResponseType.CANCEL
        tray_mod.DeckeryTray._show_system_update_hint(fake)
        fake._updater.start_system_update.assert_not_called()

    def test_no_command_means_no_button(self, tray_mod, dialog_cls):
        fake = self._fake_self(tray_mod, command=None)
        dialog_cls.return_value.run.return_value = tray_mod.Gtk.ResponseType.OK
        tray_mod.DeckeryTray._show_system_update_hint(fake)
        assert dialog_cls.call_args.kwargs["buttons"] == tray_mod.Gtk.ButtonsType.OK
        dialog_cls.return_value.add_button.assert_not_called()
        fake._updater.start_system_update.assert_not_called()

    def test_restart_dialog_has_no_button(self, tray_mod, dialog_cls):
        fake = self._fake_self(tray_mod, state="RESTART_REQUIRED")
        dialog_cls.return_value.run.return_value = tray_mod.Gtk.ResponseType.OK
        tray_mod.DeckeryTray._show_system_update_hint(fake)
        dialog_cls.return_value.add_button.assert_not_called()
        fake._updater.start_system_update.assert_not_called()


class TestUpdateBadge:
    """The update badge: on for update available / restart needed, off when
    updates are not available (packaged install without a Deckery channel)."""

    @pytest.mark.parametrize("state,badge", [
        ("UPDATE_AVAILABLE", True),
        ("RESTART_REQUIRED", True),
        ("UNAVAILABLE",      False),
        ("UP_TO_DATE",       False),
    ])
    def test_badge(self, tray_mod, monkeypatch, state, badge):
        seen = {}
        def fake_state(statuses, paused, steam, has_update, **kw):
            seen["has_update"] = has_update
            return "ok"
        monkeypatch.setattr(tray_mod, "_tray_state", fake_state)
        fake = MagicMock()
        fake._updater.state = getattr(tray_mod.UpdateState, state)
        fake._makima.lifecycle = ""
        tray_mod.DeckeryTray._refresh_tray_icon(fake)
        assert seen["has_update"] is badge
