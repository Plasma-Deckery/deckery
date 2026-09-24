"""Drive ConfigSubmenu against real GTK. Run as a subprocess by test_gtk_radio.py.

Lives in its own file because conftest.py replaces the whole gi stack with
MagicMocks for every other test in this directory. That is the right trade for
148 tests about decision logic — and exactly why it cannot see the one thing
checked here: whether GTK actually clears a radio group.

Exits non-zero with a message on failure.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import config_menu as cm

GROUP   = "kde-desktop-layout"
MEMBERS = ["KDE Desktop Layout Grid",
           "KDE Desktop Layout Horizontal",
           "KDE Desktop Layout Vertical"]
BASE    = {"name": "Steam Deck Base", "kind": "base", "parent": None,
           "enabled": True, "status": "ok", "errors": []}


def member(name, enabled):
    return {"name": name, "kind": "module", "parent": BASE["name"],
            "exclusive_group": GROUP, "enabled": enabled,
            "status": "ok", "errors": []}


def state(active):
    return [BASE] + [member(m, m == active) for m in MEMBERS]


def active_members(sub):
    return {m for m in MEMBERS if sub._slots[m].check.get_active()}


def main():
    sent = []
    sub = cm.ConfigSubmenu([], sent.append, "/tmp")
    vertical = "KDE Desktop Layout Vertical"

    sub.refresh(state(vertical))
    assert active_members(sub) == {vertical}, active_members(sub)

    # The group is switched off. Every member is set inactive one by one, which
    # GTK ignores for the one that is on — a radio group is never left empty.
    # Only the off-menu item added for this can take the dot.
    sub.refresh(state(None))
    assert active_members(sub) == set(), \
        f"a switched-off group still shows a ticked member: {active_members(sub)}"
    assert sub._group_toggles[GROUP][0].get_active() is False

    # And back. Clearing the group must not have cost the way in.
    sub.refresh(state(vertical))
    assert active_members(sub) == {vertical}, active_members(sub)

    # Every set_active() above is programmatic. None of it may reach makima:
    # a deactivation forwarded as "config disable" would race the activation.
    assert sent == [], f"programmatic updates sent IPC: {sent}"


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
