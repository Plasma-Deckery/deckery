from gi.repository import Gtk
from .common import lbl, sp


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(sp(4), False, False, 0)

    # — Red warning: unlock before updating ----------------------------------
    warn = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    warn.get_style_context().add_class("warn-box")
    warn.pack_start(lbl("! You must unlock before updating Steam", "warn-title", wrap=False),
                    False, False, 0)
    warn.pack_start(lbl(
        "While the controller config is locked, Steam gets stuck in an "
        "infinite loop at 100% CPU and cannot finish updating. "
        "Always open the tray and click \"Unlock for Steam update\" first.",
        "warn-body",
    ), False, False, 0)
    box.pack_start(warn, False, False, 0)
    box.pack_start(sp(10), False, False, 0)

    # — Amber warning: why it is locked --------------------------------------
    amber = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    amber.get_style_context().add_class("warn-box-amber")
    amber.pack_start(lbl(
        "The config is supposed to be locked because Steam overwrites it on "
        "every restart. Without the lock you would have Deckery and Steam's "
        "default bindings active at the same time.",
        "warn-body",
    ), False, False, 0)
    box.pack_start(amber, False, False, 0)
    box.pack_start(sp(12), False, False, 0)

    # — Steps ----------------------------------------------------------------
    box.pack_start(lbl("Steps", "section-divider", wrap=False), False, False, 0)

    for n, step in enumerate([
        "Tray menu  →  \"Unlock for Steam update\"",
        "Install the Steam update as normal",
        "Tray menu  →  \"Fix and Lock\"",
        "Tray returns to normal — controller works again",
    ], 1):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.get_style_context().add_class("toggle-row")
        num = Gtk.Label(label=str(n))
        num.get_style_context().add_class("page-title")
        num.set_size_request(20, -1)
        row.pack_start(num,                       False, False, 0)
        row.pack_start(lbl(step, "toggle-label"), True,  True,  0)
        box.pack_start(row, False, False, 0)

    return box
