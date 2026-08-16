import os
import gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf
from .common import lbl, sp, DIR


_SCREENSHOT = os.path.join(DIR, "docs", "assets", "tray-cropped.png")


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)

    # Left: description
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    left.pack_start(lbl(
        "Click the Deckery icon in your system tray to open the control panel.",
        "page-body",
    ), False, False, 0)
    left.pack_start(sp(14), False, False, 0)

    for item in [
        "Pause and Resume Deckery",
        "Fix and lock the Steam controller config",
        "Unlock Steam Config for Steam Updates",
        "Update Deckery",
        "Restart individual services",
        "Open this setup wizard again",
    ]:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dot = Gtk.Label(label="·")
        dot.get_style_context().add_class("toggle-label")
        row.pack_start(dot,                       False, False, 0)
        row.pack_start(lbl(item, "toggle-label"), True,  True,  0)
        left.pack_start(row, False, False, 0)

    box.pack_start(left, True, True, 0)

    # Right: tray popup screenshot
    try:
        orig = GdkPixbuf.Pixbuf.new_from_file(_SCREENSHOT)
        scale = 300 / orig.get_height()
        new_w = int(orig.get_width() * scale)
        pb = orig.scale_simple(new_w, 300, GdkPixbuf.InterpType.BILINEAR)
        img = Gtk.Image.new_from_pixbuf(pb)
        img.set_valign(Gtk.Align.START)
        box.pack_start(img, False, False, 0)
    except Exception:
        pass

    return box
