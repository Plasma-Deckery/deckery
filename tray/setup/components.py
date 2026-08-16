import os
from gi.repository import Gtk
from .common import lbl, sp, load_icon, ICONS


def _eye_image():
    img = Gtk.Image.new_from_icon_name("view-reveal-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
    img.get_style_context().add_class("component-icon-amber")
    return img


_ICON_COL_W = 38


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "Deckery remaps controller buttons to keyboard keys, shortcuts, and "
        "actions — with per-app layouts, modifier layers, and a live overlay "
        "that shows exactly what every button does at any given moment.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(14), False, False, 0)

    tray_pb = load_icon(os.path.join(ICONS, "tray-ok.svg"), 28)

    components = [
        (None,         "⌨",  "Makima Deckery",
         "The heart of Deckery — the input remapper. Reads raw controller "
         "events, emits keyboard and mouse actions."),
        (_eye_image(), None, "Deckery HUD",
         "A live overlay. See what every button does at any given moment — "
         "controls that explain themselves."),
        (tray_pb,      None, "Deckery Tray",
         "The control panel — live service status, pause, restart, "
         "one-click updates."),
        (None,         None, "Plasma KDE Dotfiles (coming)",
         "Opinionated KDE Plasma configurations, tuned for the Steam Deck's "
         "screen size and controller input."),
    ]

    for pb, char_fallback, name, desc in components:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        row.get_style_context().add_class("toggle-row")

        icon_cell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        icon_cell.set_size_request(_ICON_COL_W, -1)

        if pb is not None:
            icon_w = pb if isinstance(pb, Gtk.Widget) else Gtk.Image.new_from_pixbuf(pb)
        elif char_fallback is not None:
            icon_w = Gtk.Label(label=char_fallback)
            icon_w.get_style_context().add_class("component-icon-amber")
        else:
            # Settings icon for Plasma KDE Dotfiles (amber)
            icon_w = Gtk.Image.new_from_icon_name("settings-configure", Gtk.IconSize.LARGE_TOOLBAR)
            icon_w.get_style_context().add_class("component-icon-amber")
        icon_w.set_valign(Gtk.Align.CENTER)
        icon_w.set_halign(Gtk.Align.CENTER)
        icon_cell.pack_start(icon_w, True, True, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        info.pack_start(lbl(name, "toggle-label",    wrap=False), False, False, 0)
        info.pack_start(lbl(desc, "toggle-sublabel"            ), False, False, 0)
        row.pack_start(icon_cell, False, False, 0)
        row.pack_start(info,      True,  True,  0)
        box.pack_start(row, False, False, 0)

    return box
