import subprocess
from gi.repository import Gtk, Gdk
from .common import lbl, sp, action_btn


_KDE_CMD = ["distrobox-host-exec", "kcmshell5", "kcm_touchpad"]


def _radio_section(box, title, options):
    """
    options: list of {label, sub, default(bool), disabled(bool), after_widget(optional)}
    Each non-disabled tile gets Apply/Applied. Applied flips on click.
    """
    box.pack_start(lbl(title, "section-divider", wrap=False), False, False, 0)
    applied_idx = [next(i for i, o in enumerate(options) if o.get("default", False))]
    entries = []  # (eb, row_box, dot, apply_btn or None)

    def _apply(idx):
        applied_idx[0] = idx
        for i, (eb, row_box, dot, btn) in enumerate(entries):
            active = (i == idx)
            dot.get_style_context().remove_class("tile-dot" if active else "tile-dot-active")
            dot.get_style_context().add_class("tile-dot-active" if active else "tile-dot")
            row_box.get_style_context().remove_class(
                "tile-option" if active else "tile-option-active")
            row_box.get_style_context().add_class(
                "tile-option-active" if active else "tile-option")
            if btn:
                btn.set_label("Applied" if active else "Apply")
                btn.set_sensitive(not active)
            aw = options[i].get("after_widget")
            if aw:
                aw.set_visible(active)

    for i, opt in enumerate(options):
        is_default = opt.get("default", False)
        disabled   = opt.get("disabled", False)

        eb = Gtk.EventBox()
        eb.set_visible_window(False)
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row_box.get_style_context().add_class(
            "tile-option-active" if is_default else "tile-option")
        eb.add(row_box)

        dot = Gtk.Label(label="●")
        dot.get_style_context().add_class(
            "tile-dot-active" if is_default else "tile-dot")
        dot.set_valign(Gtk.Align.CENTER)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_lbl = lbl(opt["label"], "toggle-label",    wrap=False)
        sub_lbl  = lbl(opt["sub"],   "toggle-sublabel", wrap=False)
        if disabled:
            name_lbl.set_opacity(0.35)
            sub_lbl.set_opacity(0.35)
            dot.set_opacity(0.35)
        info.pack_start(name_lbl, False, False, 0)
        info.pack_start(sub_lbl,  False, False, 0)

        row_box.pack_start(dot,  False, False, 0)
        row_box.pack_start(info, True,  True,  0)

        if not disabled:
            apply_btn = action_btn("Applied" if is_default else "Apply")
            apply_btn.set_sensitive(not is_default)
            apply_btn.set_valign(Gtk.Align.CENTER)
            i_cap = i
            apply_btn.connect("clicked", lambda _b, idx=i_cap: _apply(idx))
            row_box.pack_start(apply_btn, False, False, 0)

            def _on_realize(w):
                win = w.get_window()
                if win:
                    win.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer"))
            eb.connect("realize", _on_realize)
            entries.append((eb, row_box, dot, apply_btn))
        else:
            entries.append((eb, row_box, dot, None))

        box.pack_start(eb, False, False, 0)

        aw = opt.get("after_widget")
        if aw:
            aw.set_no_show_all(True)
            aw.set_visible(False)
            box.pack_start(aw, False, False, 0)


def build():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl("TRANSITION FROM STEAM", "step-tag", wrap=False), False, False, 0)
    box.pack_start(lbl("Transition: Trackpads", "page-title", wrap=False), False, False, 0)
    box.pack_start(lbl(
        "Choose how each trackpad should behave after the transition.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(12), False, False, 0)

    # -- Right trackpad (first) ------------------------------------------------
    _radio_section(box, "Right trackpad", [
        {"label": "Steam trackball / mouse pointer",
         "sub":   "Steam Input handles this -- current default",
         "default": True},
        {"label": "Emulate Linux Trackpad",
         "sub":   "Simulate a standard touchpad via Deckery",
         "default": False},
    ])
    box.pack_start(sp(10), False, False, 0)

    # -- Left trackpad (second) ------------------------------------------------
    _radio_section(box, "Left trackpad", [
        {"label": "Steam scroll wheel",
         "sub":   "Steam Input handles this -- current default",
         "default": True},
        {"label": "Multitouch Gestures Only",
         "sub":   "Use for KDE pinch / rotate -- no scroll emulation",
         "default": False},
        {"label": "Deckery scroll (coming)",
         "sub":   "Custom scroll curves -- not yet available",
         "default": False,
         "disabled": True},
    ])

    # -- Footer: KDE Touchpad Settings -----------------------------------------
    footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    kde_btn = action_btn("Open KDE Touchpad Settings")
    kde_btn.connect("clicked", lambda _b: subprocess.Popen(_KDE_CMD))
    footer.pack_start(kde_btn, False, False, 0)

    return box, footer
