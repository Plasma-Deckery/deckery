import subprocess
from gi.repository import Gtk
from .common import lbl, sp, action_btn, radio_section


_KDE_CMD = ["kcmshell6", "kcm_touchpad"]


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "Choose how the right trackpad behaves after the transition.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(12), False, False, 0)

    cfg_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    cfg_box.set_margin_top(2)
    cfg_box.set_margin_bottom(6)
    cfg_box.set_margin_start(14)
    cfg_btn = action_btn("Configure this Trackpad")
    cfg_btn.connect("clicked", lambda _b: subprocess.Popen(_KDE_CMD))
    cfg_box.pack_start(cfg_btn, False, False, 0)

    section = radio_section([
        {"label": "Steam trackball / mouse pointer",
         "sub":   "Steam Input handles this — current default",
         "default": True,
         "no_btn": True},
        {"label":   "Emulate Linux Trackpad",
         "sub":     "Simulate a standard touchpad via Deckery — scroll, tap, and gestures",
         "default": False,
         "section_header": "DECKERY",
         "after_widget": cfg_box},
    ])
    box.pack_start(section, False, False, 0)
    return box
