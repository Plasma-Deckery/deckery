import subprocess
from gi.repository import Gtk, Gdk
from .common import lbl, sp, radio_section, action_btn


_PLASMA_KB_CMD = ["kcmshell6", "kcm_virtualkeyboard"]


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "Steam's keyboard is currently triggered by the X button. "
        "Moving it to Steam + X frees up X for Deckery's own bindings "
        "-- you can still open the keyboard the same way.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(16), False, False, 0)

    # Tiles 1 + 2: mutually exclusive radio pair — no status label
    section = radio_section([
        {"label":   "Steam keyboard on X button",
         "sub":     "Current state — no changes",
         "default": True,
         "no_btn":  True},
        {"label":   "Steam keyboard on Steam + X",
         "sub":     "Frees X for Deckery bindings — keyboard still accessible",
         "default": False},
    ])
    box.pack_start(section, False, False, 0)

    # "Optional" mini-label before independent tile
    box.pack_start(sp(10), False, False, 0)
    box.pack_start(lbl("OPTIONAL", "step-tag", wrap=False), False, False, 0)
    box.pack_start(sp(4), False, False, 0)

    # Tile 3: independent — just opens Plasma keyboard settings, no radio state
    plasma_eb = Gtk.EventBox()
    plasma_eb.set_visible_window(False)
    plasma_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    plasma_row.get_style_context().add_class("tile-option")
    plasma_eb.add(plasma_row)

    plasma_dot = Gtk.Label(label="●")
    plasma_dot.get_style_context().add_class("tile-dot")
    plasma_dot.set_valign(Gtk.Align.CENTER)

    plasma_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    plasma_info.pack_start(lbl("Use Plasma's on-screen keyboard", "toggle-label",    wrap=False), False, False, 0)
    plasma_info.pack_start(lbl("Replaces Steam's keyboard with the system keyboard", "toggle-sublabel", wrap=False), False, False, 0)

    cfg_btn = action_btn("Configure")
    cfg_btn.set_valign(Gtk.Align.CENTER)
    cfg_btn.connect("clicked", lambda _: subprocess.Popen(_PLASMA_KB_CMD))

    plasma_row.pack_start(plasma_dot,  False, False, 0)
    plasma_row.pack_start(plasma_info, True,  True,  0)
    plasma_row.pack_start(cfg_btn,     False, False, 0)

    def _on_realize(w):
        win = w.get_window()
        if win:
            win.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer"))
    plasma_eb.connect("realize", _on_realize)

    box.pack_start(plasma_eb, False, False, 0)
    return box
