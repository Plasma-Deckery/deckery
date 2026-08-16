import threading
from gi.repository import Gtk, GLib
from .common import lbl, sp, action_btn, radio_section
from .widgets import L3Visual
from . import vdf_config


def build():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "Deckery clears all button shortcuts from the Steam Desktop config "
        "and activates its own default bindings via Makima. "
        "You can restore the Steam config from the tray menu at any time.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(14), False, False, 0)

    # — Footer: L3 "Try it now" — hidden until Apply succeeds
    l3_sub  = lbl("Press L3 to open the HUD — your config is live.",
                  "toggle-sublabel", wrap=False)
    l3_visual = L3Visual()
    l3_visual.set_valign(Gtk.Align.CENTER)

    l3_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    l3_row.get_style_context().add_class("toggle-row")
    l3_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    l3_info.pack_start(lbl("Try it now", "toggle-label", wrap=False), False, False, 0)
    l3_info.pack_start(l3_sub, False, False, 0)
    l3_row.pack_start(l3_info,    True,  True,  0)
    l3_row.pack_start(l3_visual,  False, False, 0)

    # Wrap in a box that starts hidden; wizard tracks visibility via notify::visible
    l3_footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    l3_footer.pack_start(l3_row, False, False, 0)
    l3_footer.set_no_show_all(True)
    l3_footer.set_visible(False)

    def _do_clear():
        path = vdf_config.find_vdf()
        if not path:
            return
        try:
            vdf_config.clear_all_bindings(path)
            # Reveal footer L3 widget
            GLib.idle_add(_show_footer)
        except Exception:
            pass

    def _show_footer():
        l3_footer.set_no_show_all(False)
        l3_footer.show_all()

    def _on_apply_deckery():
        threading.Thread(target=_do_clear, daemon=True).start()

    section = radio_section([
        {"label":   "Steam Input handles buttons",
         "sub":     "Current state — Steam Desktop layout is active",
         "default": True,
         "no_btn":  True},
        {"label":   "Deckery handles buttons",
         "sub":     "Clears Steam shortcuts, loads Deckery default config",
         "default": False,
         "section_header": "DECKERY",
         "on_apply": _on_apply_deckery},
    ])
    box.pack_start(section, False, False, 0)
    return box, l3_footer
