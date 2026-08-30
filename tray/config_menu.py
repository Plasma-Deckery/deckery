"""
config_menu — Controller Bindings submenu for the Deckery tray.

Each config gets exactly one dedicated slot (CheckMenuItem + MenuItem pair)
identified by name.  Slots are never reused for a different config — they
stay in the submenu permanently (hidden when their config is absent).

Update strategy:
  - Config already has a slot → update in-place (label, active, visible)
  - Config is new            → append a fresh slot; dbusmenu propagates it
  - Config was removed       → hide its slot (reappears if the config returns)

dbusmenu propagates both property changes (label, active, visible) and
append() of new GTK items to the panel without a full re-fetch.

Data flow:
  DeckeryTray polls state.json → calls ConfigSubmenu.refresh(configs)
  ConfigSubmenu decides whether anything changed and updates widgets.
  User interactions (toggle, error click) are dispatched via the ipc callable.
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject

import logging
import subprocess
from dataclasses import dataclass

log = logging.getLogger("deckery-tray")


@dataclass
class _ConfigSlot:
    """One row in the Controller Bindings submenu, bound to a single config name.

    ``check``     Gtk.CheckMenuItem — shown for ok / warning configs.
    ``error``     Gtk.MenuItem      — shown for error configs; opens a dialog.
    ``toggle_id`` GObject handler ID for "toggled" on ``check``; used to block
                  the signal during programmatic set_active() calls.
    ``error_text`` Last known full error message for the dialog.
    """
    check:      Gtk.CheckMenuItem
    error:      Gtk.MenuItem
    toggle_id:  int
    error_text: str = ""


class ConfigSubmenu:
    """Controller Bindings submenu widget.

    Parameters
    ----------
    initial_configs:
        Config list from the first state.json read — used to build the initial
        set of slots in alphabetical order before the panel first fetches them.
    ipc:
        Callable that sends a makima IPC command string, e.g. _makima_ipc.
    config_dir:
        Path opened by the "Open config folder" item.
    """

    def __init__(self, initial_configs: list, ipc: callable, config_dir: str):
        self._ipc        = ipc
        self._config_dir = config_dir
        self._slots:     dict[str, _ConfigSlot] = {}   # name → slot
        self._last:      list | None = None
        self._sep:       Gtk.SeparatorMenuItem | None = None  # set after initial loop

        self._parent  = _icon_item("Controller Bindings", "input-gamepad")
        self._submenu = Gtk.Menu()
        self._parent.set_submenu(self._submenu)

        # Build initial slots in alphabetical order.
        # _sep is still None here, so _create_slot() appends to end.
        for cfg in sorted(initial_configs, key=lambda c: c["name"]):
            self._create_slot(cfg["name"])

        self._sep = Gtk.SeparatorMenuItem()
        self._sep.set_no_show_all(True)
        self._sep.hide()
        self._submenu.append(self._sep)

        open_cfg = _icon_item("Open config folder", "folder")
        open_cfg.connect("activate", lambda _: subprocess.Popen(["xdg-open", self._config_dir]))
        self._submenu.append(open_cfg)

        self._submenu.show_all()

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def item(self) -> Gtk.MenuItem:
        """The 'Controller Bindings' MenuItem — append this to the root menu."""
        return self._parent

    def refresh(self, configs: list) -> None:
        """Update submenu contents if configs changed.

        Idempotent: safe to call on every poll cycle.  Does nothing when the
        config list is identical to the last rendered state.
        """
        if configs == self._last:
            return
        self._last = configs
        self._apply(configs)

    # ── Private ───────────────────────────────────────────────────────────────

    def _create_slot(self, name: str) -> _ConfigSlot:
        """Create a new slot for *name* and add it to the submenu.

        During initial construction (_sep is None) slots are appended to the
        end.  When called at runtime (_sep exists) the slot is inserted
        immediately before the separator so the "Open config folder" link stays
        at the bottom.

        The slot remains in the submenu permanently — hidden when its config is
        absent, shown when it is present.
        """
        chk = Gtk.CheckMenuItem(label="")
        chk.set_no_show_all(True)
        chk.hide()
        def _on_toggle(widget, n=name):
            self._ipc(f"config {'enable' if widget.get_active() else 'disable'} {n}")
        toggle_id = chk.connect("toggled", _on_toggle)

        err = Gtk.MenuItem(label="")
        err.set_no_show_all(True)
        err.hide()
        def _on_error_click(widget, n=name):
            _show_error_dialog(n, self._slots[n].error_text)
        err.connect("activate", _on_error_click)

        if self._sep is None:
            # Initial build — append in the order _create_slot is called
            self._submenu.append(chk)
            self._submenu.append(err)
        else:
            # Runtime growth — insert before separator
            children = self._submenu.get_children()
            pos      = children.index(self._sep)
            self._submenu.insert(chk, pos)
            self._submenu.insert(err, pos + 1)

        slot = _ConfigSlot(check=chk, error=err, toggle_id=toggle_id)
        self._slots[name] = slot
        return slot

    def _apply(self, configs: list) -> None:
        config_map = {c["name"]: c for c in configs}

        for name, cfg in config_map.items():
            if name not in self._slots:
                self._create_slot(name)

            slot    = self._slots[name]
            enabled = cfg["enabled"]
            status  = cfg.get("status", "ok")
            is_base = "::" not in name
            errors  = cfg.get("errors", [])

            slot.error_text = "\n\n".join(e.get("message", "") for e in errors) or "Unknown error"

            if status == "error":
                slot.error.set_label(f"🛑 {name}")
                slot.check.hide()
                slot.error.show()
            else:
                label_text = f"⚠ {name}" if status == "warning" else name
                GObject.signal_handler_block(slot.check, slot.toggle_id)
                try:
                    slot.check.set_label(label_text)
                    slot.check.set_active(enabled)
                    slot.check.set_sensitive(not is_base)
                finally:
                    GObject.signal_handler_unblock(slot.check, slot.toggle_id)
                slot.error.hide()
                slot.check.show()

        # Hide slots whose config is no longer present
        for name, slot in self._slots.items():
            if name not in config_map:
                slot.check.hide()
                slot.error.hide()

        if self._sep:
            self._sep.show() if config_map else self._sep.hide()


# ── Module-level helpers ──────────────────────────────────────────────────────

def _icon_item(label: str, icon_name: str) -> Gtk.MenuItem:
    item = Gtk.ImageMenuItem(label=label)
    img  = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
    item.set_image(img)
    item.set_always_show_image(True)
    return item


def _show_error_dialog(name: str, msg: str) -> None:
    """Open a scrollable dialog showing the full error text for a config."""
    dlg = Gtk.Dialog(title=f"Config error — {name}", modal=True)
    dlg.set_default_size(600, 300)
    dlg.add_button("Close", Gtk.ResponseType.CLOSE)
    sw = Gtk.ScrolledWindow()
    sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    sw.set_margin_start(12); sw.set_margin_end(12)
    sw.set_margin_top(12);  sw.set_margin_bottom(12)
    tv = Gtk.TextView()
    tv.set_editable(False); tv.set_cursor_visible(False)
    tv.set_monospace(True)
    tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    tv.get_buffer().set_text(msg)
    sw.add(tv)
    dlg.get_content_area().pack_start(sw, True, True, 0)
    dlg.show_all(); dlg.run(); dlg.destroy()
