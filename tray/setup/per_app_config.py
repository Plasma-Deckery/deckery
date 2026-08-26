import os
import glob
from gi.repository import Gtk
from .common import lbl, sp, action_btn, DECKERY_CONFIGS
from .ipc import hud_toggle


def _app_name(filename: str) -> str:
    base = os.path.basename(filename)
    if "::" in base:
        app_id = base.split("::", 1)[1].replace(".toml", "")
        short  = app_id.rsplit(".", 1)[-1].capitalize()
        return short, app_id
    return base.replace(".toml", ""), ""


def _scan_apps():
    pattern = os.path.join(DECKERY_CONFIGS, "*::*.toml")
    return sorted(
        (p, _app_name(p)) for p in glob.glob(pattern)
    )


def build() -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.pack_start(lbl(
        "Makima switches to a different binding profile when a specific app "
        "is in focus. All discovered profiles are enabled by default.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(14), False, False, 0)

    apps = _scan_apps()
    toggles = {}

    if not apps:
        box.pack_start(lbl(
            "No per-app configs found in ~/.config/deckery/",
            "toggle-sublabel",
        ), False, False, 0)
    else:
        for filepath, (short_name, app_id) in apps:
            sw = Gtk.Switch()
            sw.set_active(True)
            sw.set_valign(Gtk.Align.CENTER)
            toggles[filepath] = sw

            # Eye button -- previews HUD with this config
            eye_btn = Gtk.Button()
            eye_btn.add(Gtk.Image.new_from_icon_name("view-visible", Gtk.IconSize.SMALL_TOOLBAR))
            eye_btn.get_style_context().add_class("btn-eye")
            eye_btn.set_relief(Gtk.ReliefStyle.NONE)
            eye_btn.set_valign(Gtk.Align.CENTER)
            eye_btn.set_tooltip_text(f"Preview HUD with {short_name} config")
            eye_btn.connect("clicked", lambda _b: hud_toggle())

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.get_style_context().add_class("toggle-row")

            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            info.pack_start(lbl(short_name, "toggle-label", wrap=False), False, False, 0)
            info.pack_start(lbl(app_id or os.path.basename(filepath),
                                "toggle-sublabel", wrap=False), False, False, 0)

            row.pack_start(info,    True,  True,  0)
            row.pack_start(eye_btn, False, False, 0)
            row.pack_start(sw,      False, False, 0)
            box.pack_start(row, False, False, 0)

    box.pack_start(sp(10), False, False, 0)

    apply_btn = action_btn("Apply")
    status    = lbl("", "toggle-sublabel")

    def _on_apply(_b):
        # TODO: persist enabled/disabled state
        enabled = sum(1 for sw in toggles.values() if sw.get_active())
        apply_btn.set_label("Applied")
        apply_btn.set_sensitive(False)
        status.set_text(
            f"{enabled} of {len(apps)} per-app profiles active."
            if apps else "Nothing to apply."
        )

    apply_btn.connect("clicked", _on_apply)
    box.pack_start(apply_btn, False, False, 0)
    box.pack_start(status,    False, False, 4)
    return box
