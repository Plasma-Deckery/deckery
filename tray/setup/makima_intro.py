import subprocess
from gi.repository import Gtk
from .common import lbl, sp, action_btn, MAKIMA_CONFIGS


_DOCS_URL = "https://plasma-deckery.github.io/deckery/"
_ICON_COL_W = 38


# -- Icon helpers (same as hud_try.py) ----------------------------------------

def _reload_icon():
    w = Gtk.Label(label="↻")
    w.get_style_context().add_class("component-icon")
    return w


def _l1_pill():
    w = Gtk.Label(label="L1")
    w.get_style_context().add_class("key-pill")
    return w


def _app_pill():
    w = Gtk.Label(label="App")
    w.get_style_context().add_class("pill-teal")
    return w


def _eye_image():
    img = Gtk.Image.new_from_icon_name("view-reveal-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
    img.get_style_context().add_class("component-icon")
    return img


# -- Row builder --------------------------------------------------------------

def _icon_row(icon, char, title, sub):
    """icon: Gtk.Widget or None (uses char label instead)."""
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
    row.get_style_context().add_class("toggle-row")

    icon_cell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    icon_cell.set_size_request(_ICON_COL_W, -1)

    if icon is not None:
        icon_w = icon
    else:
        icon_w = Gtk.Label(label=char)
        icon_w.get_style_context().add_class("component-icon")
    icon_w.set_valign(Gtk.Align.CENTER)
    icon_w.set_halign(Gtk.Align.CENTER)
    icon_cell.pack_start(icon_w, True, True, 0)

    info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    info.pack_start(lbl(title, "toggle-label",    wrap=False), False, False, 0)
    info.pack_start(lbl(sub,   "toggle-sublabel"            ), False, False, 0)

    row.pack_start(icon_cell, False, False, 0)
    row.pack_start(info,      True,  True,  0)
    return row


# -- Page ---------------------------------------------------------------------

def build():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "The heart of Deckery — the input remapper. "
        "Remaps controller buttons to keyboard keys, shortcuts, and actions, "
        "with per-app layouts, modifier layers, and trackpad gesture devices.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(16), False, False, 0)

    features = [
        (_app_pill(),    None, "Per-app layouts",
         "Switches profiles automatically when an app comes into focus"),
        (_l1_pill(),     None, "Modifier layers",
         "Hold a button to access a second set of bindings"),
        (_eye_image(),   None, "Live overlay",
         "The HUD shows the active layout at any given moment"),
        (_reload_icon(), None, "Hot-reloadable",
         "Change bindings on the fly without restarting"),
    ]

    for icon, char, title, sub in features:
        box.pack_start(_icon_row(icon, char, title, sub), False, False, 0)

    # Footer
    footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    footer.set_margin_top(10)

    cfg_btn = action_btn("Open Config Folder")
    cfg_btn.connect("clicked", lambda _b: subprocess.Popen(
        ["xdg-open", MAKIMA_CONFIGS]
    ))

    ref_btn = action_btn("Deckery Reference")
    ref_btn.connect("clicked", lambda _b: subprocess.Popen(
        ["xdg-open", _DOCS_URL]
    ))

    footer.pack_start(cfg_btn, False, False, 0)
    footer.pack_start(ref_btn, False, False, 0)

    return box, footer
