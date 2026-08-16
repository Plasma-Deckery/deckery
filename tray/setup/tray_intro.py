import os
from gi.repository import Gtk
from .common import lbl, sp, load_icon, ICONS


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "The tray icon sits in your system tray and shows Deckery's health "
        "at a glance. Click it to open the menu — pause services, trigger a "
        "fix, or open this wizard again.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(16), False, False, 0)
    box.pack_start(lbl("Icon states", "section-divider", wrap=False), False, False, 0)

    states = [
        ("tray-ok.svg",     "All services running, Steam config locked"),
        ("tray-warn.svg",   "Needs attention, paused, or loading"),
        ("tray-err.svg",    "Service failed or Steam overrode its config"),
        ("tray-update.svg", "A Deckery update is available"),
    ]

    for fname, desc in states:
        pb = load_icon(os.path.join(ICONS, fname), 22)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.get_style_context().add_class("toggle-row")
        if pb:
            row.pack_start(Gtk.Image.new_from_pixbuf(pb), False, False, 0)
        else:
            dot = Gtk.Label(label="●")
            dot.get_style_context().add_class("toggle-label")
            row.pack_start(dot, False, False, 0)
        row.pack_start(lbl(desc, "toggle-sublabel"), True, True, 0)
        box.pack_start(row, False, False, 0)

    return box
