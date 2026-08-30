#!/usr/bin/env python3
"""
dbusmenu dynamic-item test.

Submenu starts with two items that toggle labels every 2s.
Every 6s a NEW item is appended / a previously appended item is hidden.
Specifically tests three mechanisms:

  [1] label change on existing item      — known to work
  [2] show() on pre-registered hidden item — does this work?
  [3] append() of a brand-new GTK widget  — does THIS work?

Phase A (0–6s):   items [1] and [2-hidden] and [3-not-yet-created] exist
Phase B (6–12s):  show [2], append [3]
Phase C (12–18s): hide [2], hide [3]  (item [3] stays in tree, just hidden)
Phase D (18–24s): show [2], show [3]  (reuse of [3] — was it registered?)
... repeats
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, AyatanaAppIndicator3, GLib

import os

_ICONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

indicator = AyatanaAppIndicator3.Indicator.new_with_path(
    "dbusmenu-test",
    "tray-ok",
    AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
    _ICONS,
)
indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
indicator.set_title("dbusmenu test")

# ── Build initial menu ────────────────────────────────────────────────────────
menu       = Gtk.Menu()
sub_parent = Gtk.MenuItem(label="Submenu →")
submenu    = Gtk.Menu()
sub_parent.set_submenu(submenu)
menu.append(sub_parent)

# [1] Always-present item — label toggles every 2s
item_1 = Gtk.MenuItem(label="[1] label-toggle: EINS")
submenu.append(item_1)

# [2] Pre-registered but initially hidden — show/hide tested
item_2 = Gtk.MenuItem(label="[2] pre-registered, initially hidden")
item_2.set_no_show_all(True)
item_2.hide()
submenu.append(item_2)

# [3] Does NOT exist yet — will be appended later
item_3 = [None]   # box so the closure can write to it

menu.append(Gtk.SeparatorMenuItem())
quit_item = Gtk.MenuItem(label="Quit")
quit_item.connect("activate", lambda _: Gtk.main_quit())
menu.append(quit_item)

menu.show_all()
indicator.set_menu(menu)

# ── Tick: label toggle every 2s ───────────────────────────────────────────────
_tick = [0]

def on_label_tick():
    _tick[0] += 1
    n = "EINS" if _tick[0] % 2 == 0 else "ZWEI"
    item_1.set_label(f"[1] label-toggle: {n}")
    print(f"  label tick {_tick[0]:3d} → {n}", flush=True)
    return GLib.SOURCE_CONTINUE

GLib.timeout_add(2000, on_label_tick)

# ── Phase: add/remove every 6s ────────────────────────────────────────────────
_phase = [0]

def on_phase_tick():
    _phase[0] += 1
    p = _phase[0] % 4   # 0=hide-both  1=show+append  2=hide-both  3=show-both(reuse)

    if p == 1:
        print("\nPhase B — show [2] (pre-registered) + append [3] (brand new)", flush=True)
        item_2.show()
        if item_3[0] is None:
            it = Gtk.MenuItem(label="[3] brand-new append")
            submenu.append(it)
            it.show()
            item_3[0] = it
            print("  [3] appended fresh", flush=True)
        else:
            item_3[0].show()
            print("  [3] shown (was already in tree)", flush=True)

    elif p == 2:
        print("\nPhase C — hide [2] + hide [3]", flush=True)
        item_2.hide()
        if item_3[0]:
            item_3[0].hide()

    elif p == 3:
        print("\nPhase D — show [2] + show [3] (reuse)", flush=True)
        item_2.show()
        if item_3[0]:
            item_3[0].show()

    else:  # p == 0
        print("\nPhase A — hide both", flush=True)
        item_2.hide()
        if item_3[0]:
            item_3[0].hide()

    return GLib.SOURCE_CONTINUE

GLib.timeout_add(6000, on_phase_tick)

print("""
Running.  Open the 'Submenu →' in the tray and watch:

  [1]  always visible, label toggles EINS/ZWEI every 2s
  [2]  pre-registered hidden item  — appears/disappears every 6s
  [3]  brand-new appended item     — first appears after 6s

Ctrl-C or 'Quit' to stop.
""", flush=True)
Gtk.main()
