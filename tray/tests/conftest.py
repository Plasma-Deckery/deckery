"""
conftest.py — Test environment setup for deckery-tray tests.

Mocks the entire gi stack so tests run without a display or a GLib main loop.
Covers GLib, Gio (used by SteamConfigWatcher / Updater) and Gtk, GdkPixbuf,
AyatanaAppIndicator3 (used by deckery-tray.py, tested via test_tray.py).

GLib.idle_add / io_add_watch / timeout_add_seconds are captured but never
executed — state assertions work because _set_state writes self._state
synchronously before the idle_add call.
"""

import sys
from unittest.mock import MagicMock

# ── Mock gi.repository (full stack) ──────────────────────────────────────────
#
# Must happen before any import of the tray modules.

_glib = MagicMock()
_glib.SOURCE_CONTINUE = True
_glib.SOURCE_REMOVE   = False
_glib.IO_IN           = 1

_gio = MagicMock()

sys.modules.setdefault("gi",                                    MagicMock())
sys.modules["gi.repository"]                                    = MagicMock()
sys.modules["gi.repository.GLib"]                               = _glib
sys.modules["gi.repository.Gio"]                                = _gio
sys.modules.setdefault("gi.repository.Gtk",                     MagicMock())
sys.modules.setdefault("gi.repository.GdkPixbuf",               MagicMock())
sys.modules.setdefault("gi.repository.AyatanaAppIndicator3",    MagicMock())
