from gi.repository import Gtk, GdkPixbuf
from .common import lbl, sp


_ICON_COL_W = 38


def _l1_pill():
    w = Gtk.Label(label="L1")
    w.get_style_context().add_class("key-pill-amber")
    return w


_ICON_PX = 22   # forced pixel size for all row icons


def _eye_image():
    img = Gtk.Image.new_from_icon_name("view-reveal-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
    img.set_pixel_size(_ICON_PX)
    img.get_style_context().add_class("component-icon-amber")
    return img


def _icon_row(icon, char, css, title, sub):
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
    row.get_style_context().add_class("toggle-row")

    # Fixed-width cell — icon must fit inside, never pushes text out of alignment
    cell = Gtk.Box()
    cell.set_size_request(_ICON_COL_W, _ICON_COL_W)

    if icon is not None:
        icon_w = icon
    else:
        icon_w = Gtk.Label(label=char)
        icon_w.get_style_context().add_class(css or "component-icon")
    icon_w.set_valign(Gtk.Align.CENTER)
    icon_w.set_halign(Gtk.Align.CENTER)
    cell.pack_start(icon_w, True, True, 0)

    info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    info.pack_start(lbl(title, "toggle-label",    wrap=False), False, False, 0)
    info.pack_start(lbl(sub,   "toggle-sublabel"            ), False, False, 0)

    row.pack_start(cell, False, False, 0)
    row.pack_start(info, True,  True,  0)
    return row


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "Full desktop productivity on the Steam Deck — "
        "controller in hand, no physical keyboard needed.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(16), False, False, 0)

    touchpad_img = Gtk.Image.new_from_icon_name("input-touchpad-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
    touchpad_img.set_pixel_size(_ICON_PX)
    touchpad_img.get_style_context().add_class("component-icon-amber")

    try:
        steam_pb = Gtk.IconTheme.get_default().load_icon("steam", _ICON_PX, 0)
        steam_img = Gtk.Image.new_from_pixbuf(steam_pb)
    except Exception:
        steam_img = Gtk.Image.new_from_icon_name("emblem-unreadable-symbolic",
                                                  Gtk.IconSize.LARGE_TOOLBAR)
        steam_img.set_pixel_size(_ICON_PX)
        steam_img.get_style_context().add_class("component-icon-amber")

    items = [
        (_l1_pill(),   None, None, "Map Controller to Keyboard and Shortcuts",
         "Per-app layouts and modifier layers — every button reprogrammable"),
        (touchpad_img, None, None, "Map Trackpads",
         "Configure left and right trackpad as mouse pointer, "
         "gesture surface, or scroll wheel"),
        (_eye_image(), None, None, "Live overlay shows every binding",
         "The HUD renders what every button does right now, "
         "switching automatically with the active app"),
        (steam_img,    None, None, "Steam-independent",
         "Runs without the Steam process — "
         "works in any desktop app at any time"),
    ]

    for icon, char, css, title, sub in items:
        box.pack_start(_icon_row(icon, char, css, title, sub), False, False, 0)

    return box
