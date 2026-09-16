"""
test_config_menu.py — Unit tests for ConfigSubmenu._apply() logic.

GTK is fully mocked via conftest.py — no display required.
Tests verify the decision logic: which widget is shown/hidden, what labels are
set, what IPC commands are fired — based on the config data passed to refresh().

The GTK mocks mean show(), hide(), set_label(), set_active(), set_sensitive()
are all MagicMock callables that record their calls for assertion.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config_menu as cm


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cfg(name, enabled=True, status="ok", errors=None, kind="app", parent=None):
    """Build a config dict matching makima's state.json format."""
    return {"name": name, "kind": kind, "parent": parent, "enabled": enabled,
            "status": status, "errors": errors or []}


APP_CFG  = "Firefox"
BASE_CFG = "Steam Deck"
# Nested rows carry a tree glyph; a lone entry in its group is the last one.
APP_ROW  = f"└─ {APP_CFG}"


@pytest.fixture
def ipc():
    return MagicMock()


@pytest.fixture
def sub(ipc):
    """ConfigSubmenu seeded with one app config and the base config."""
    return cm.ConfigSubmenu(
        initial_configs=[_cfg(APP_CFG), _cfg(BASE_CFG, kind="base")],
        ipc=ipc,
        config_dir="/tmp/cfg",
    )


# ── refresh() idempotency ─────────────────────────────────────────────────────

class TestRefreshIdempotency:
    def test_no_reapply_when_unchanged(self, sub):
        configs = [_cfg(APP_CFG)]
        sub.refresh(configs)
        slot = sub._slots[APP_CFG]
        slot.check.reset_mock()
        slot.error.reset_mock()

        sub.refresh(configs)  # identical list — should be a no-op

        slot.check.set_label.assert_not_called()
        slot.error.set_label.assert_not_called()

    def test_reapply_when_enabled_changes(self, sub):
        sub.refresh([_cfg(APP_CFG, enabled=True)])
        slot = sub._slots[APP_CFG]
        slot.check.reset_mock()

        sub.refresh([_cfg(APP_CFG, enabled=False)])

        slot.check.set_active.assert_called_with(False)

    def test_reapply_when_status_changes(self, sub):
        sub.refresh([_cfg(APP_CFG, status="ok")])
        slot = sub._slots[APP_CFG]
        slot.error.reset_mock()

        sub.refresh([_cfg(APP_CFG, status="error")])

        slot.error.show.assert_called()


# ── ok status ─────────────────────────────────────────────────────────────────

class TestOkStatus:
    def test_check_shown_error_hidden(self, sub):
        sub.refresh([_cfg(APP_CFG)])
        slot = sub._slots[APP_CFG]
        slot.check.show.assert_called()
        slot.error.hide.assert_called()

    def test_plain_label(self, sub):
        sub.refresh([_cfg(APP_CFG)])
        sub._slots[APP_CFG].check.set_label.assert_called_with(APP_ROW)

    def test_active_true_when_enabled(self, sub):
        sub.refresh([_cfg(APP_CFG, enabled=True)])
        sub._slots[APP_CFG].check.set_active.assert_called_with(True)

    def test_active_false_when_disabled(self, sub):
        sub.refresh([_cfg(APP_CFG, enabled=False)])
        sub._slots[APP_CFG].check.set_active.assert_called_with(False)

    def test_app_config_shows_a_checkbox(self, sub):
        sub.refresh([_cfg(APP_CFG)])
        slot = sub._slots[APP_CFG]
        slot.check.show.assert_called()
        slot.error.hide.assert_called()

    def test_base_config_has_no_checkbox(self, sub):
        # The base cannot be switched off, so it gets no checkbox at all.
        sub.refresh([_cfg(BASE_CFG, kind="base")])
        slot = sub._slots[BASE_CFG]
        slot.error.set_label.assert_called_with(BASE_CFG)
        slot.error.show.assert_called()
        slot.check.hide.assert_called()
        slot.check.show.assert_not_called()

    def test_healthy_base_is_not_clickable(self, sub):
        # Nothing to report → no dialog to open.
        sub.refresh([_cfg(BASE_CFG, kind="base")])
        sub._slots[BASE_CFG].error.set_sensitive.assert_called_with(False)


# ── warning status ────────────────────────────────────────────────────────────

class TestWarningStatus:
    def test_check_shown_with_warning_prefix(self, sub):
        sub.refresh([_cfg(APP_CFG, status="warning")])
        slot = sub._slots[APP_CFG]
        slot.check.set_label.assert_called_with(f"⚠ {APP_ROW}")
        slot.check.show.assert_called()
        slot.error.hide.assert_called()

    def test_base_keeps_warning_prefix_and_becomes_clickable(self, sub):
        # The base has no checkbox, so its warning rides on the plain row —
        # which turns sensitive so the message dialog can be opened.
        sub.refresh([_cfg(BASE_CFG, kind="base", status="warning",
                          errors=[{"message": "no bindings defined"}])])
        slot = sub._slots[BASE_CFG]
        slot.error.set_label.assert_called_with(f"⚠ {BASE_CFG}")
        slot.error.set_sensitive.assert_called_with(True)
        slot.error.show.assert_called()
        assert slot.error_text == "no bindings defined"


# ── error status ──────────────────────────────────────────────────────────────

class TestErrorStatus:
    def test_error_shown_check_hidden(self, sub):
        sub.refresh([_cfg(APP_CFG, status="error")])
        slot = sub._slots[APP_CFG]
        slot.error.show.assert_called()
        slot.check.hide.assert_called()

    def test_error_label_has_stop_sign(self, sub):
        sub.refresh([_cfg(APP_CFG, status="error")])
        sub._slots[APP_CFG].error.set_label.assert_called_with(f"🛑 {APP_ROW}")

    def test_error_text_from_errors_list(self, sub):
        errors = [{"message": "missing key 'foo'"}, {"message": "bad value"}]
        sub.refresh([_cfg(APP_CFG, status="error", errors=errors)])
        assert sub._slots[APP_CFG].error_text == "missing key 'foo'\n\nbad value"

    def test_error_text_fallback_when_empty(self, sub):
        sub.refresh([_cfg(APP_CFG, status="error", errors=[])])
        assert sub._slots[APP_CFG].error_text == "Unknown error"

    def test_base_error_wins_over_the_plain_row(self, sub):
        # Status is checked before kind, so a broken base reports itself with a
        # stop sign instead of being drawn as a silent greyed-out row.
        sub.refresh([_cfg(BASE_CFG, kind="base", status="error",
                          errors=[{"message": "no device section"}])])
        slot = sub._slots[BASE_CFG]
        slot.error.set_label.assert_called_with(f"🛑 {BASE_CFG}")
        slot.error.set_sensitive.assert_called_with(True)
        slot.check.hide.assert_called()
        assert slot.error_text == "no device section"


# ── removed config ────────────────────────────────────────────────────────────

class TestRemovedConfig:
    def test_absent_config_leaves_the_layout(self, sub):
        sub.refresh([_cfg(APP_CFG)])
        assert any(r.name == APP_CFG for r in cm.display_rows([_cfg(APP_CFG)]))

        sub.refresh([])  # APP_CFG removed

        assert sub._layout == []

    def test_slot_reappears_when_config_returns(self, sub):
        sub.refresh([])                       # hide everything
        sub.refresh([_cfg(APP_CFG)])          # APP_CFG is back
        slot = sub._slots[APP_CFG]
        slot.check.show.assert_called()


# ── separator visibility ──────────────────────────────────────────────────────

class TestSeparatorVisibility:
    def test_separator_shown_when_configs_present(self, sub):
        sub.refresh([_cfg(APP_CFG)])
        sub._sep.show.assert_called()

    def test_separator_hidden_when_no_configs(self, sub):
        sub.refresh([])
        sub._sep.hide.assert_called()


# ── runtime slot creation ─────────────────────────────────────────────────────

class TestRuntimeSlotCreation:
    def test_new_config_gets_a_slot(self, sub):
        new_cfg = "Dolphin"
        assert new_cfg not in sub._slots

        sub.refresh([_cfg(new_cfg)])

        assert new_cfg in sub._slots

    def test_new_slot_is_shown(self, sub):
        new_cfg = "Dolphin"
        sub.refresh([_cfg(new_cfg)])
        sub._slots[new_cfg].check.show.assert_called()


# ── IPC calls on toggle ───────────────────────────────────────────────────────

class TestIpcOnToggle:
    def test_enable_command_sent(self, sub, ipc):
        sub.refresh([_cfg(APP_CFG)])
        slot = sub._slots[APP_CFG]
        # Simulate the user checking the item (widget reports active=True)
        slot.check.get_active.return_value = True
        # Fire the toggled signal handler directly
        slot.check.connect.call_args_list  # recorded during _create_slot
        # Retrieve and call the handler stored via connect("toggled", handler)
        toggle_handler = slot.check.connect.call_args[0][1]
        toggle_handler(slot.check)
        ipc.assert_called_with(f"config enable {APP_CFG}")

    def test_disable_command_sent(self, sub, ipc):
        sub.refresh([_cfg(APP_CFG)])
        slot = sub._slots[APP_CFG]
        slot.check.get_active.return_value = False
        toggle_handler = slot.check.connect.call_args[0][1]
        toggle_handler(slot.check)
        ipc.assert_called_with(f"config disable {APP_CFG}")


# ── exclusive groups ──────────────────────────────────────────────────────────

def _grouped(name, group, enabled=False, parent=BASE_CFG):
    cfg = _cfg(name, enabled=enabled, kind="module", parent=parent)
    cfg["exclusive_group"] = group
    return cfg


class TestExclusiveGroups:
    def test_group_members_are_radio_items(self, sub):
        sub.refresh([
            _cfg(BASE_CFG, kind="base"),
            _grouped("Layout Horizontal", "layout", enabled=True),
        ])
        cm.Gtk.RadioMenuItem.assert_called()

    def test_group_members_are_drawn_adjacently(self):
        rows = cm.display_rows([
            _cfg(BASE_CFG, kind="base"),
            _grouped("Layout Zulu",  "layout"),
            _grouped("Layout Alpha", "layout"),
            _cfg("Manual", kind="module", parent=BASE_CFG),
        ])
        names = [r.name for r in rows]
        assert abs(names.index("Layout Zulu") - names.index("Layout Alpha")) == 1

    def test_selecting_a_member_sends_only_enable(self, sub, ipc):
        sub.refresh([
            _cfg(BASE_CFG, kind="base"),
            _grouped("Layout Horizontal", "layout", enabled=True),
            _grouped("Layout Vertical",   "layout"),
        ])
        ipc.reset_mock()
        slot = sub._slots["Layout Vertical"]
        slot.check.get_active.return_value = True
        slot.check.connect.call_args[0][1](slot.check)
        ipc.assert_called_once_with("config enable Layout Vertical")

    def test_deselecting_a_member_sends_nothing(self, sub, ipc):
        """GTK deactivates the previous radio item; makima already did that."""
        sub.refresh([
            _cfg(BASE_CFG, kind="base"),
            _grouped("Layout Horizontal", "layout", enabled=True),
            _grouped("Layout Vertical",   "layout"),
        ])
        ipc.reset_mock()
        slot = sub._slots["Layout Horizontal"]
        slot.check.get_active.return_value = False
        slot.check.connect.call_args[0][1](slot.check)
        ipc.assert_not_called()

    def test_ungrouped_module_still_sends_disable(self, sub, ipc):
        sub.refresh([_cfg(BASE_CFG, kind="base"), _cfg("Voice Control", kind="module", parent=BASE_CFG)])
        ipc.reset_mock()
        slot = sub._slots["Voice Control"]
        slot.check.get_active.return_value = False
        slot.check.connect.call_args[0][1](slot.check)
        ipc.assert_called_once_with("config disable Voice Control")


class TestGroupHeadings:
    """A group is drawn as a named cluster, not a run of unrelated radio ticks."""

    def test_a_heading_row_precedes_the_members(self):
        rows = cm.display_rows([
            _cfg(BASE_CFG, kind="base"),
            _grouped("KDE Desktop Layout Horizontal", "kde-desktop-layout"),
            _grouped("KDE Desktop Layout Vertical",   "kde-desktop-layout"),
        ])
        names = [r.name for r in rows]
        heading = names.index("kde-desktop-layout")
        assert rows[heading].heading
        assert heading < names.index("KDE Desktop Layout Horizontal")

    def test_the_heading_is_named_after_its_members(self):
        rows = cm.display_rows([
            _cfg(BASE_CFG, kind="base"),
            _grouped("KDE Desktop Layout Horizontal", "kde-desktop-layout"),
            _grouped("KDE Desktop Layout Vertical",   "kde-desktop-layout"),
        ])
        heading = next(r for r in rows if r.heading)
        # The slug is an identifier, not something to put in front of a user.
        assert heading.text == "KDE Desktop Layout"

    def test_members_drop_what_the_heading_already_says(self):
        rows = cm.display_rows([
            _cfg(BASE_CFG, kind="base"),
            _grouped("KDE Desktop Layout Horizontal", "kde-desktop-layout"),
            _grouped("KDE Desktop Layout Vertical",   "kde-desktop-layout"),
        ])
        labels = {r.name: r.text for r in rows if not r.heading}
        assert labels["KDE Desktop Layout Horizontal"] == "Horizontal"
        assert labels["KDE Desktop Layout Vertical"]   == "Vertical"

    def test_members_without_a_shared_prefix_keep_their_names(self):
        rows = cm.display_rows([
            _cfg(BASE_CFG, kind="base"),
            _grouped("Alpha", "layout"),
            _grouped("Beta",  "layout"),
        ])
        heading = next(r for r in rows if r.heading)
        labels  = {r.name: r.text for r in rows if not r.heading}
        assert heading.text == "layout"
        assert labels["Alpha"] == "Alpha"
        assert labels["Beta"]  == "Beta"

    def test_a_shared_prefix_is_whole_words_only(self):
        # "Layout H" is a shared character run, not a shared name.
        assert cm._shared_prefix(["Layout Horizontal", "Layout Hyprland"]) == "Layout"

    def test_a_lone_member_keeps_its_full_name(self):
        # Nothing to factor out, and the heading must not swallow the only label.
        assert cm._shared_prefix(["KDE Desktop Layout Grid"]) == ""

    def test_the_apps_heading_still_works(self, sub):
        sub.refresh([_cfg(BASE_CFG, kind="base"), _cfg("Firefox", kind="app")])
        rows = cm.display_rows([_cfg(BASE_CFG, kind="base"), _cfg("Firefox", kind="app")])
        assert any(r.heading and r.name == "Apps" for r in rows)


class TestGroupMembershipChanges:
    """A module can gain or lose a group across an update."""

    def test_gaining_a_group_replaces_the_checkbox_with_a_radio(self, sub):
        sub.refresh([_cfg(BASE_CFG, kind="base"),
                     _cfg("Layout Alpha", kind="module", parent=BASE_CFG)])
        assert sub._slots["Layout Alpha"].group is None
        before = sub._slots["Layout Alpha"].check

        sub.refresh([_cfg(BASE_CFG, kind="base"),
                     _grouped("Layout Alpha", "layout")])

        slot = sub._slots["Layout Alpha"]
        assert slot.group == "layout"
        # A new widget, not the old one relabelled — the toggle handler on the
        # old checkbox would still send "disable", which makima now refuses.
        assert slot.check is not before

    def test_losing_a_group_replaces_the_radio_with_a_checkbox(self, sub):
        sub.refresh([_cfg(BASE_CFG, kind="base"),
                     _grouped("Layout Alpha", "layout")])
        before = sub._slots["Layout Alpha"].check

        sub.refresh([_cfg(BASE_CFG, kind="base"),
                     _cfg("Layout Alpha", kind="module", parent=BASE_CFG)])

        slot = sub._slots["Layout Alpha"]
        assert slot.group is None
        assert slot.check is not before

    def test_an_unchanged_group_keeps_its_widgets(self, sub):
        sub.refresh([_cfg(BASE_CFG, kind="base"),
                     _grouped("Layout Alpha", "layout", enabled=True)])
        before = sub._slots["Layout Alpha"].check

        sub.refresh([_cfg(BASE_CFG, kind="base"),
                     _grouped("Layout Alpha", "layout", enabled=False)])

        assert sub._slots["Layout Alpha"].check is before
