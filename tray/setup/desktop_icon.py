import os
import shutil
from gi.repository import Gtk
from .common import lbl, sp, action_btn, info_row, DIR


_MENU_DST    = os.path.expanduser("~/.local/share/applications/deckery.desktop")
_DESKTOP_DST = os.path.expanduser("~/Desktop/deckery.desktop")


def _status_widget(ok: bool) -> Gtk.Widget:
    dot = Gtk.Label(label="●")
    dot.get_style_context().add_class("req-ok" if ok else "req-fail")
    dot.set_valign(Gtk.Align.CENTER)
    txt = lbl("Installed" if ok else "Not found", "toggle-sublabel", wrap=False)
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    row.pack_start(dot, False, False, 0)
    row.pack_start(txt, False, False, 0)
    return row


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "Deckery is already available in your application menu. "
        "Optionally add a shortcut to the Desktop too — "
        "handy if the tray ever stops and you need to restart quickly.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(16), False, False, 0)

    # Application menu row (always installed after setup)
    box.pack_start(info_row(
        "Application Menu",
        "~/.local/share/applications/deckery.desktop",
        _status_widget(os.path.exists(_MENU_DST)),
    ), False, False, 0)

    # Desktop row (optional, placeable)
    placed = os.path.exists(_DESKTOP_DST)
    btn    = action_btn("Applied" if placed else "Place on Desktop")
    btn.set_sensitive(not placed)
    status = lbl("", "toggle-sublabel")

    def _on_place(_b):
        try:
            shutil.copy2(os.path.join(DIR, "deckery.desktop"), _DESKTOP_DST)
            os.chmod(_DESKTOP_DST, 0o755)
            btn.set_label("Applied")
            btn.set_sensitive(False)
            status.set_text("Saved to ~/Desktop — also available in the application menu.")
        except Exception as e:
            status.set_text(f"Error: {e}")

    btn.connect("clicked", _on_place)
    box.pack_start(info_row("Desktop Shortcut", "~/Desktop/deckery.desktop", btn),
                   False, False, 0)
    box.pack_start(status, False, False, 4)
    return box
