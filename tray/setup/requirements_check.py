"""
requirements_check.py -- System requirement checks and fix actions.
"""
import getpass
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from .common import lbl, action_btn
from .ipc import open_konsole


# -- Checks -------------------------------------------------------------------

def check_input_group() -> bool:
    try:
        out = subprocess.run(
            ["id", "-Gn"], capture_output=True, text=True, timeout=3
        ).stdout
        return "input" in out.split()
    except Exception:
        return False


def check_sudo_chattr() -> bool:
    """Check whether the HOST has the deckery-chattr sudoers rule."""
    try:
        r = subprocess.run(
            ["distrobox-host-exec", "bash", "-c",
             "test -f /etc/sudoers.d/deckery-chattr && echo ok"],
            capture_output=True, text=True, timeout=5,
        )
        return "ok" in r.stdout
    except Exception:
        return False


# -- Fix actions --------------------------------------------------------------

def fix_input_group():
    user = getpass.getuser()
    open_konsole("Add user to input group", "\n".join([
        f"sudo usermod -aG input {user}",
        "  && echo '  OK -- please log out and back in to apply.'",
        "  || echo '  ERROR -- check permissions.'",
    ]))


def fix_sudo_chattr():
    user = getpass.getuser()
    rule = f"{user} ALL=(ALL) NOPASSWD: /usr/bin/chattr"
    open_konsole("Install sudoers rule for chattr", "\n".join([
        f"echo '{rule}' | sudo tee /etc/sudoers.d/deckery-chattr > /dev/null",
        "  && sudo chmod 440 /etc/sudoers.d/deckery-chattr",
        "  && echo '  OK -- rule installed.'",
        "  || echo '  ERROR -- check permissions.'",
    ]))


# -- Reusable requirement row widget ------------------------------------------

def req_row(title: str, subtitle: str, fix_cb):
    """
    Build a requirement status row.
    Returns (row_widget, update_fn).
    update_fn(bool) sets the dot colour and fix-button sensitivity.
    """
    dot = Gtk.Label(label="●")
    dot.get_style_context().add_class("req-pending")
    dot.set_valign(Gtk.Align.CENTER)

    fix_btn = action_btn("Fix")
    fix_btn.set_sensitive(False)

    def _on_fix(_b):
        fix_cb()
        for cls in ("req-pending", "req-ok", "req-fail"):
            dot.get_style_context().remove_class(cls)
        dot.get_style_context().add_class("req-pending")
        stat.set_text("Opening terminal...")
        fix_btn.set_label("Fix")
        fix_btn.set_sensitive(False)

    fix_btn.connect("clicked", _on_fix)

    stat = Gtk.Label(label="Checking...", xalign=1)
    stat.get_style_context().add_class("toggle-sublabel")

    info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    info.pack_start(lbl(title,    "toggle-label",    wrap=False), False, False, 0)
    info.pack_start(lbl(subtitle, "toggle-sublabel"            ), False, False, 0)

    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.get_style_context().add_class("toggle-row")
    row.pack_start(dot,     False, False, 0)
    row.pack_start(info,    True,  True,  0)
    row.pack_start(stat,    False, False, 0)
    row.pack_start(fix_btn, False, False, 0)

    def update(ok: bool):
        for cls in ("req-pending", "req-ok", "req-fail"):
            dot.get_style_context().remove_class(cls)
        dot.get_style_context().add_class("req-ok" if ok else "req-fail")
        stat.set_text("OK" if ok else "Not set up")
        fix_btn.set_sensitive(not ok)

    return row, update
