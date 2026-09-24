"""The one test that needs real GTK rather than the conftest mocks.

`Gtk.RadioMenuItem.set_active(False)` on the member that is on does nothing:
GTK will not leave a radio group with nothing selected. A group switched off
therefore kept showing a ticked member, and clicking that member emitted no
`toggled`, so it could not even be switched back on there. ConfigSubmenu works
around it with an extra radio item that belongs to the group but is never
appended to any menu.

None of that is visible to a MagicMock, whose set_active() simply records the
call. So the check runs in a subprocess with the real gi stack.
"""

import os
import subprocess
import sys

import pytest

_PROBE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtk_radio_probe.py")


def _real_gtk_available() -> bool:
    return subprocess.run(
        [sys.executable, "-c",
         "import gi; gi.require_version('Gtk','3.0'); from gi.repository import Gtk"],
        capture_output=True,
    ).returncode == 0


@pytest.mark.skipif(not _real_gtk_available(), reason="GTK 3 introspection unavailable")
def test_a_switched_off_group_shows_no_ticked_member():
    r = subprocess.run([sys.executable, _PROBE], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr or r.stdout
