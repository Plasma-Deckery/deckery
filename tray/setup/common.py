"""
common.py -- Shared constants, CSS, and widget helpers for the setup wizard.
"""
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf

# -- Paths --------------------------------------------------------------------

_SETUP_DIR  = os.path.dirname(os.path.abspath(__file__))   # tray/setup/
_TRAY_DIR   = os.path.dirname(_SETUP_DIR)                  # tray/
DIR         = os.path.dirname(_TRAY_DIR)                   # deckery/ root
ICONS       = os.path.join(_TRAY_DIR, "icons")
HUD_ASSETS  = os.path.join(os.path.dirname(DIR), "deckery-hud", "assets")
SENTINEL      = os.path.expanduser("~/.config/deckery/.onboarding-done")
MAKIMA_CONFIGS = os.path.expanduser("~/.config/makima")

# -- Colors -------------------------------------------------------------------

C_BG    = (0.031, 0.031, 0.071)
C_TEAL  = (0.45,  0.90,  0.82)
C_AMBER = (1.0,   0.792, 0.2)

# -- Page registry ------------------------------------------------------------

PAGES = [
    "welcome",
    "components",
    "requirements",
    "hud_try",
    "tray_intro",
    "tray_menu",
    "makima_intro",
    "setup_step1",
    "setup_step2",
    "trackpad_right",
    "trackpad_left",
    "desktop_icon",
    "steam_updates_info",
    "per_app_config",
    "done",
]

SKIPPABLE = {"desktop_icon"}

# -- Page titles (shown fixed above scroll in wizard) -------------------------

TITLES = {
    "welcome":            "Welcome to Deckery",
    "components":         "What is Deckery?",
    "requirements":       "Requirements",
    "hud_try":            "Deckery HUD",
    "tray_intro":         "The Tray Icon",
    "tray_menu":          "The Tray Menu",
    "makima_intro":       "Makima Deckery",
    "setup_step1":        "Steam's On-Screen Keyboard",
    "setup_step2":        "Steam's Button Mapping",
    "trackpad_right":     "Right Trackpad",
    "trackpad_left":      "Left Trackpad",
    "desktop_icon":       "Desktop Launcher",
    "steam_updates_info": "One Note Before You Go",
    "per_app_config":     "Per-App Configuration",
    "done":               "You're all set!",
}

STEP_TAGS = {
    "setup_step1":    "TRANSITION FROM STEAM",
    "setup_step2":    "TRANSITION FROM STEAM",
    "trackpad_right": "TRANSITION FROM STEAM",
    "trackpad_left":  "TRANSITION FROM STEAM",
}

# -- CSS ----------------------------------------------------------------------

CSS = b"""
window { background-color: #080812; }

.wizard-right {
    background-color: #080812;
    padding: 28px 36px 24px 28px;
}

.page-title {
    color: #73E6D1;
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 10px;
}

.page-body {
    color: rgba(255,255,255,0.75);
    font-size: 13px;
}

.step-tag {
    color: #73E6D1;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    margin-bottom: 6px;
}

.section-divider {
    color: rgba(255,255,255,0.15);
    font-size: 11px;
    margin-top: 6px;
    margin-bottom: 6px;
}

.btn-primary {
    background-color: #73E6D1;
    background-image: none;
    color: #080812;
    font-weight: bold;
    font-size: 14px;
    border-radius: 6px;
    padding: 10px 28px;
    min-width: 100px;
    box-shadow: none;
    text-shadow: none;
    transition: background-color 120ms linear;
}
button.btn-primary:hover {
    opacity: 0.82;
}

.btn-back {
    background-color: transparent;
    color: rgba(255,255,255,0.45);
    font-size: 13px;
    padding: 10px 14px;
    border-radius: 6px;
}
.btn-back:hover {
    color: rgba(255,255,255,0.80);
    background-color: rgba(255,255,255,0.06);
}

.btn-skip {
    background-color: transparent;
    color: rgba(255,255,255,0.30);
    font-size: 12px;
    padding: 10px 14px;
    border-radius: 6px;
}
.btn-skip:hover { color: rgba(255,255,255,0.60); }

.btn-action {
    background-color: rgba(115,230,209,0.10);
    color: #73E6D1;
    font-size: 12px;
    font-weight: bold;
    border-radius: 6px;
    padding: 7px 16px;
    border: 1px solid rgba(115,230,209,0.25);
}
.btn-action:hover { background-color: rgba(115,230,209,0.20); }
.btn-action:disabled {
    color: rgba(115,230,209,0.28);
    border-color: rgba(115,230,209,0.10);
}

.toggle-row {
    background-color: rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 11px 15px;
    margin-bottom: 8px;
}
.toggle-label    { color: rgba(255,255,255,0.90); font-size: 13px; }
.toggle-sublabel { color: rgba(255,255,255,0.45); font-size: 11px; }

.component-icon {
    color: #73E6D1;
    font-size: 26px;
    font-weight: bold;
}

.tile-option {
    background-color: rgba(255,255,255,0.04);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 5px;
    border: 1px solid rgba(255,255,255,0.07);
}
.tile-option-active {
    background-color: rgba(115,230,209,0.09);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 5px;
    border: 1px solid rgba(115,230,209,0.38);
}
.tile-dot        { color: rgba(255,255,255,0.22); font-size: 11px; }
.tile-dot-active { color: #73E6D1; font-size: 11px; }

.component-icon-amber {
    color: #FFCA33;
    font-size: 20px;
    font-weight: bold;
}

.btn-reload {
    background-color: transparent;
    border-radius: 50%;
    padding: 4px 6px;
    color: rgba(255,255,255,0.30);
    font-size: 15px;
}
.btn-reload:hover {
    color: rgba(255,255,255,0.70);
    background-color: rgba(255,255,255,0.07);
}

.btn-eye {
    background-color: transparent;
    border-radius: 6px;
    padding: 3px 8px;
    color: rgba(255,255,255,0.28);
    font-size: 13px;
}
.btn-eye:hover { color: rgba(255,255,255,0.65); }

.key-pill {
    color: rgba(255,255,255,0.80);
    border: 1px solid rgba(255,255,255,0.28);
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: bold;
    background-color: rgba(255,255,255,0.07);
}
.key-pill-amber {
    color: #FFCA33;
    border: 1px solid rgba(255,202,51,0.55);
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
    font-weight: bold;
    background-color: rgba(255,202,51,0.10);
}
.pill-teal {
    color: #73E6D1;
    border: 1px solid rgba(115,230,209,0.45);
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 10px;
    font-weight: bold;
    background-color: rgba(115,230,209,0.10);
}

.warn-box {
    background-color: rgba(255,90,90,0.10);
    border-radius: 8px;
    padding: 14px 16px;
    border: 1px solid rgba(255,90,90,0.40);
    margin-bottom: 4px;
}
.warn-title {
    color: #FF5A5A;
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 6px;
}
.warn-body {
    color: rgba(255,255,255,0.80);
    font-size: 12px;
}

.warn-box-amber {
    background-color: rgba(255,202,51,0.08);
    border-radius: 8px;
    padding: 14px 16px;
    border: 1px solid rgba(255,202,51,0.35);
    margin-bottom: 4px;
}
.warn-title-amber {
    color: #FFCA33;
    font-size: 13px;
    font-weight: bold;
    margin-bottom: 4px;
}

.req-ok      { color: #73E6D1; font-size: 15px; }
.req-fail    { color: #FF5A5A; font-size: 15px; }
.req-pending { color: rgba(255,255,255,0.20); font-size: 15px; }

.color-green  { color: #73E6D1; }
.color-yellow { color: #FFCA33; }
.color-red    { color: #FF5A5A; }
"""

# -- Widget helpers -----------------------------------------------------------

def lbl(text, css_class, wrap=True, mw=50):
    l = Gtk.Label(label=text, xalign=0)
    l.get_style_context().add_class(css_class)
    if wrap:
        l.set_line_wrap(True)
        l.set_line_wrap_mode(0)   # WORD, not CHAR -- prevents mid-word hyphenation
        l.set_max_width_chars(mw)
    return l


def sp(h=14):
    b = Gtk.Box()
    b.set_size_request(-1, h)
    return b


def action_btn(label: str) -> Gtk.Button:
    b = Gtk.Button(label=label)
    b.get_style_context().add_class("btn-action")
    b.set_relief(Gtk.ReliefStyle.NONE)
    return b


def info_row(title, subtitle, right=None) -> Gtk.Box:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.get_style_context().add_class("toggle-row")
    info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    info.pack_start(lbl(title,    "toggle-label",    wrap=False), False, False, 0)
    info.pack_start(lbl(subtitle, "toggle-sublabel", wrap=False), False, False, 0)
    row.pack_start(info, True, True, 0)
    if right is not None:
        right.set_valign(Gtk.Align.CENTER)
        row.pack_start(right, False, False, 0)
    return row


def radio_section(options):
    """
    Radio-tile selector used on multiple wizard pages.
    options: list of dicts — label, sub, default(bool), disabled(bool),
             after_widget(Gtk.Widget), on_apply(callable)
    Returns a Gtk.Box container.
    """
    container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    applied_idx = [next((i for i, o in enumerate(options) if o.get("default", False)), -1)]
    entries = []  # (eb, row_box, dot, apply_btn | None)

    def _apply(idx):
        applied_idx[0] = idx
        for i, (eb, row_box, dot, btn) in enumerate(entries):
            active = (i == idx)
            # Always update dot and row style
            dot.get_style_context().remove_class("tile-dot" if active else "tile-dot-active")
            dot.get_style_context().add_class("tile-dot-active" if active else "tile-dot")
            row_box.get_style_context().remove_class(
                "tile-option" if active else "tile-option-active")
            row_box.get_style_context().add_class(
                "tile-option-active" if active else "tile-option")
            # Update button if present
            if btn is not None:
                custom_label    = options[i].get("btn_label")
                always_sensitive = options[i].get("btn_always_sensitive", False)
                if not custom_label:
                    btn.set_label("Applied" if active else "Apply")
                btn.set_sensitive(not active or always_sensitive)
            aw = options[i].get("after_widget")
            if aw:
                if active:
                    aw.set_no_show_all(False)
                    aw.show_all()
                else:
                    aw.set_no_show_all(True)
                    aw.set_visible(False)

    for i, opt in enumerate(options):
        is_default = opt.get("default", False)
        disabled   = opt.get("disabled", False)

        # Optional section divider before this tile
        sec_hdr = opt.get("section_header")
        if sec_hdr:
            container.pack_start(sp(10), False, False, 0)
            container.pack_start(lbl(sec_hdr, "step-tag", wrap=False), False, False, 0)
            container.pack_start(sp(4),  False, False, 0)

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

        no_btn       = opt.get("no_btn", False)
        custom_label = opt.get("btn_label")
        always_sens  = opt.get("btn_always_sensitive", False)

        if not disabled and not no_btn:
            init_label = custom_label if custom_label else ("Applied" if is_default else "Apply")
            apply_btn  = action_btn(init_label)
            apply_btn.set_sensitive((not is_default) or always_sens)
            apply_btn.set_valign(Gtk.Align.CENTER)
            on_apply_cb = opt.get("on_apply")
            i_cap = i

            def _on_click(_b, idx=i_cap, cb=on_apply_cb):
                _apply(idx)
                if cb:
                    cb()

            apply_btn.connect("clicked", _on_click)
            row_box.pack_start(apply_btn, False, False, 0)

            def _on_realize(w):
                win = w.get_window()
                if win:
                    win.set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer"))
            eb.connect("realize", _on_realize)
            entries.append((eb, row_box, dot, apply_btn))
        else:
            entries.append((eb, row_box, dot, None))

        container.pack_start(eb, False, False, 0)

        aw = opt.get("after_widget")
        if aw:
            aw.set_no_show_all(True)
            aw.set_visible(False)
            container.pack_start(aw, False, False, 0)

    return container


def load_icon(path: str, size: int = 32):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
    except Exception:
        return None
