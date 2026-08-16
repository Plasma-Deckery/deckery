from gi.repository import Gtk
from .common import lbl, sp


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "Deckery is running. Press L3 (left stick click) to open the HUD "
        "overlay at any time. You can reopen this wizard from the tray menu.",
        "page-body",
    ), False, False, 0)
    return box
