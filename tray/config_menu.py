"""
config_menu — Controller Bindings submenu for the Deckery tray.

Each config gets exactly one dedicated slot (CheckMenuItem + MenuItem pair)
identified by name.  Slots are never reused for a different config — they
stay in the submenu permanently (hidden when their config is absent).

Rows are grouped: each base config, its included modules indented beneath it,
then an "Apps" heading with the per-application overrides. Grouping comes from
the "kind" and "parent" fields makima writes into state.json — the tray never
inspects config files itself.

Update strategy:
  - Same set of configs   → update slots in-place (label, active, visible)
  - Set or order changed  → re-append every item in display order
  - Config was removed    → its slot leaves the menu (reappears if it returns)

dbusmenu propagates property changes and append() of new GTK items, but not
insert(). Anything that changes the order therefore has to re-append the lot.

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


@dataclass(frozen=True)
class Row:
    """One line in the submenu: either a config or the "Apps" heading.

    ``prefix`` carries the tree glyph a nested entry is drawn with.
    """
    name:    str
    prefix:  str = ""
    heading: bool = False


def display_rows(configs: list) -> list[Row]:
    """Order configs for display: each base, its modules beneath it, then apps.

    Pure — no GTK, no I/O. Grouping comes entirely from the "kind" and "parent"
    fields; a config missing them lands in the top-level group.
    """
    def group(kind: str) -> list:
        return sorted((c for c in configs if c.get("kind") == kind),
                      key=lambda c: c["name"].lower())

    def nest(entries: list) -> list[Row]:
        last = len(entries) - 1
        return [Row(c["name"], "└─ " if i == last else "├─ ")
                for i, c in enumerate(entries)]

    bases   = group("base")
    modules = group("module")
    apps    = group("app")
    base_names = {b["name"] for b in bases}

    rows: list[Row] = []
    for base in bases:
        rows.append(Row(base["name"]))
        rows += nest([m for m in modules if m.get("parent") == base["name"]])

    # A module whose parent is gone, or a file that would not parse: neither can
    # be nested, but both still need a row — that row is where the error shows.
    strays = [m for m in modules if m.get("parent") not in base_names]
    strays += [c for c in configs if c.get("kind") not in ("base", "module", "app")]
    rows += [Row(c["name"]) for c in sorted(strays, key=lambda c: c["name"].lower())]

    if apps:
        rows.append(Row("Apps", heading=True))
        rows += nest(apps)
    return rows


@dataclass
class _ConfigSlot:
    """One row in the Controller Bindings submenu, bound to a single config name.

    ``check``     Gtk.CheckMenuItem — shown for toggleable ok / warning configs.
    ``error``     Gtk.MenuItem      — the non-toggleable row: every error, plus
                  the base config in any state. Sensitive only when it has
                  something to report, and then a click opens the dialog.
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
        self._layout:    list | None = None            # last rendered row order

        self._parent  = _icon_item("Controller Bindings", "input-gamepad")
        self._submenu = Gtk.Menu()
        self._parent.set_submenu(self._submenu)

        self._apps_heading = Gtk.MenuItem(label="Apps")
        self._apps_heading.set_sensitive(False)

        self._sep = Gtk.SeparatorMenuItem()
        self._sep.set_no_show_all(True)
        self._sep.hide()

        self._open_cfg = _icon_item("Open config folder", "folder")
        self._open_cfg.connect("activate", lambda _: subprocess.Popen(["xdg-open", self._config_dir]))

        self._apply(initial_configs)

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
        """Create the widget pair for *name*. Placement is done by _relayout."""
        chk = Gtk.CheckMenuItem(label="")
        def _on_toggle(widget, n=name):
            self._ipc(f"config {'enable' if widget.get_active() else 'disable'} {n}")
        toggle_id = chk.connect("toggled", _on_toggle)

        err = Gtk.MenuItem(label="")
        def _on_error_click(widget, n=name):
            _show_error_dialog(n, self._slots[n].error_text)
        err.connect("activate", _on_error_click)

        slot = _ConfigSlot(check=chk, error=err, toggle_id=toggle_id)
        self._slots[name] = slot
        return slot

    def _relayout(self, rows: list) -> None:
        """Re-append every item so the menu matches *rows* top to bottom."""
        for child in self._submenu.get_children():
            self._submenu.remove(child)
        for row in rows:
            if row.heading:
                self._submenu.append(self._apps_heading)
                continue
            slot = self._slots[row.name]
            self._submenu.append(slot.check)
            self._submenu.append(slot.error)
        self._submenu.append(self._sep)
        self._submenu.append(self._open_cfg)
        self._submenu.show_all()

    def _apply(self, configs: list) -> None:
        config_map = {c["name"]: c for c in configs}
        rows       = display_rows(configs)

        for row in rows:
            if not row.heading and row.name not in self._slots:
                self._create_slot(row.name)

        layout = [(r.heading, r.name, r.prefix) for r in rows]
        if layout != self._layout:
            self._layout = layout
            self._relayout(rows)

        for row in rows:
            if row.heading:
                continue
            cfg     = config_map[row.name]
            slot    = self._slots[row.name]
            status  = cfg.get("status", "ok")
            errors  = cfg.get("errors", [])
            label   = f"{row.prefix}{row.name}"

            slot.error_text = "\n\n".join(e.get("message", "") for e in errors) or "Unknown error"

            label_text = f"⚠ {label}" if status == "warning" else label

            if status == "error":
                slot.error.set_label(f"🛑 {label}")
                slot.error.set_sensitive(True)
                slot.check.hide()
                slot.error.show()
            elif cfg.get("kind") == "base":
                # The base config is the device itself — switching it off would
                # leave makima with nothing to apply. A tick that is always set
                # and never clickable is noise, so the base is drawn as a plain
                # row instead, greyed out like the "Apps" group. A warning makes
                # it clickable, and the click opens the message dialog.
                slot.error.set_label(label_text)
                slot.error.set_sensitive(bool(errors))
                slot.check.hide()
                slot.error.show()
            else:
                GObject.signal_handler_block(slot.check, slot.toggle_id)
                try:
                    slot.check.set_label(label_text)
                    slot.check.set_active(cfg["enabled"])
                finally:
                    GObject.signal_handler_unblock(slot.check, slot.toggle_id)
                slot.error.hide()
                slot.check.show()

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
