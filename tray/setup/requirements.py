import threading
from gi.repository import Gtk, GLib
from .common import lbl, sp
from .requirements_check import (
    check_input_group, check_sudo_chattr,
    fix_input_group, fix_sudo_chattr,
    req_row,
)


def build():
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

    box.pack_start(lbl(
        "Two permissions Deckery needs before it can run properly.",
        "page-body",
    ), False, False, 0)
    box.pack_start(sp(16), False, False, 0)

    checks = [
        ("Add User to Input Group",
         "Needed to read raw controller events from /dev/input",
         check_input_group, fix_input_group),
        ("Passwordless Steam Config Lock",
         "Needed to lock Steam's controller config without a sudo password",
         check_sudo_chattr, fix_sudo_chattr),
    ]

    update_fns = []
    for title, subtitle, check_fn, fix_fn in checks:
        row_w, update = req_row(title, subtitle, fix_fn)
        box.pack_start(row_w, False, False, 0)
        update_fns.append((check_fn, update))

    def _run():
        for fn, upd in update_fns:
            GLib.idle_add(upd, fn())

    threading.Thread(target=_run, daemon=True).start()

    return box
