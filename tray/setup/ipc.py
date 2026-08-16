"""
ipc.py -- IPC helpers: HUD D-Bus toggle, terminal launcher.
"""
import subprocess
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio


def hud_toggle():
    """Toggle the deckery-hud overlay via D-Bus. Silently ignores errors."""
    try:
        bus   = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            "de.plasma_deckery.hud", "/de/plasma_deckery/hud",
            "de.plasma_deckery.hud", None,
        )
        proxy.call_sync("Toggle", None, Gio.DBusCallFlags.NONE, 2000, None)
    except Exception:
        pass


def open_konsole(header: str, body: str):
    """Open a Konsole terminal on the host (via distrobox-host-exec) running body."""
    script = "\n".join([
        "echo ''",
        "echo '  +--------------------------------------+'",
        "echo '  |  Deckery Setup                      |'",
        "echo '  +--------------------------------------+'",
        f"echo '  {header}'",
        "echo ''",
        body,
        "echo ''",
        "read -p '  Press Enter to close...'",
    ])
    subprocess.Popen([
        "distrobox-host-exec", "konsole", "--noclose",
        "-e", "bash", "-c", script,
    ])
