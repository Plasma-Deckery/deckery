from gi.repository import Gtk, Gdk
from .common import lbl, sp
from .ipc import hud_toggle
from .widgets import L3Visual


def _icon_cell(widget):
    cell = Gtk.Box()
    cell.set_size_request(34, -1)
    widget.set_halign(Gtk.Align.CENTER)
    widget.set_valign(Gtk.Align.CENTER)
    cell.pack_start(widget, True, True, 0)
    return cell


def _feature_row(icon_w, title, sub):
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.get_style_context().add_class("toggle-row")
    row.pack_start(_icon_cell(icon_w), False, False, 0)
    info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    info.pack_start(lbl(title, "toggle-label",    wrap=False), False, False, 0)
    info.pack_start(lbl(sub,   "toggle-sublabel"            ), False, False, 0)
    row.pack_start(info, True, True, 0)
    return row


def _l1_pill():
    w = Gtk.Label(label="L1")
    w.get_style_context().add_class("key-pill")
    return w


def _app_pill():
    w = Gtk.Label(label="App")
    w.get_style_context().add_class("pill-teal")
    return w


def build():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "A live overlay that renders the Steam Deck and draws callout lines "
        "to every bound action — so your controls are always visible, "
        "not just memorised.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(12), False, False, 0)

    box.pack_start(_feature_row(
        Gtk.Image.new_from_icon_name("view-visible", Gtk.IconSize.BUTTON),
        "See what every button does right now",
        "Works for the active app — look it up instead of memorising",
    ), False, False, 0)
    box.pack_start(_feature_row(
        Gtk.Image.new_from_icon_name("media-playback-pause-symbolic", Gtk.IconSize.BUTTON),
        "Dry-run mode",
        "Explore your layout without triggering actions",
    ), False, False, 0)
    box.pack_start(_feature_row(
        _l1_pill(),
        "Modifier layers",
        "Hold a button to reveal a second set of bindings",
    ), False, False, 0)
    box.pack_start(_feature_row(
        _app_pill(),
        "Per-app layouts",
        "Config switches automatically with the focused window",
    ), False, False, 0)

    # — Footer: Try it now ---------------------------------------------------
    l3 = L3Visual()
    eb = Gtk.EventBox()
    eb.add(l3)
    eb.set_valign(Gtk.Align.CENTER)
    eb.set_tooltip_text("Click to toggle HUD")

    def _on_realize(w):
        win = w.get_window()
        if win:
            win.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer"))
    eb.connect("realize", _on_realize)

    def _on_click(*_):
        hud_toggle()
    eb.connect("button-press-event", lambda *_: _on_click())

    footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.get_style_context().add_class("toggle-row")
    info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    info.pack_start(lbl("Try it now",             "toggle-label",    wrap=False), False, False, 0)
    info.pack_start(lbl("Press L3 or click here", "toggle-sublabel", wrap=False), False, False, 0)
    row.pack_start(info, True,  True,  0)
    row.pack_start(eb,   False, False, 0)

    footer.pack_start(row, False, False, 0)

    return box, footer
