#!/usr/bin/env python3
"""
deckery-tray — System tray icon for Deckery services.

Polls systemd user services for status, provides context-sensitive controls
(Pause/Resume/Start/Stop), OSD toggle, config access, updates, and links.
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GdkPixbuf, AyatanaAppIndicator3, GLib, Gio

import json
import os
import socket
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from updater import Updater, UpdateState, local_version
from steam_config_watcher import SteamConfigWatcher

# ── Paths ─────────────────────────────────────────────────────────────────────

_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICONS      = os.path.join(_DIR, "tray", "icons")
_ICON_OK     = os.path.join(_ICONS, "tray-ok.svg")      # dark bg + white D-pad
_ICON_WARN   = os.path.join(_ICONS, "tray-warn.svg")    # orange bg + white D-pad
_ICON_ERR    = os.path.join(_ICONS, "tray-err.svg")     # red bg   + white D-pad
_ICON_UPDATE = os.path.join(_ICONS, "tray-update.svg")  # dark bg + cyan badge

# Small dot SVGs for the menu status column (12 px, no D-pad shape)
_DOT_OK       = os.path.join(_ICONS, "dot-ok.svg")
_DOT_PAUSED   = os.path.join(_ICONS, "dot-paused.svg")
_DOT_ERR      = os.path.join(_ICONS, "dot-err.svg")
_DOT_INACTIVE = os.path.join(_ICONS, "dot-inactive.svg")

_STATE_JSON         = "/tmp/makima-state.json"
_MAKIMA_SOCK        = "/tmp/makima-control.sock"
_CONFIG_DIR         = os.path.expanduser("~/.config/makima")
_GITHUB_DISCUSSIONS = "https://github.com/Plasma-Deckery/deckery/discussions"

# D-Bus address for deckery-hud
_HUD_BUS  = "de.plasma_deckery.hud"
_HUD_PATH = "/de/plasma_deckery/hud"

POLL_MS = 2000  # polling interval for service status (ms)

# Maps _tray_state() result key → (icon_path, tooltip label)
_TRAY_ICONS: dict[str, tuple[str, str]] = {
    "ok":     (_ICON_OK,     "Deckery: running"),
    "warn":   (_ICON_WARN,   "Deckery: needs attention"),
    "err":    (_ICON_ERR,    "Deckery: error"),
    "update": (_ICON_UPDATE, "Deckery: update available"),
}

def _version_label(v: str) -> str:
    """Format the tray header label for a given version string.
    Returns 'Deckery vX.Y.Z' normally, or just 'Deckery' when the version
    is unknown (e.g. repo has no tags yet)."""
    return f"Deckery v{v}" if v != "unknown" else "Deckery"


# Services to monitor: key → systemd unit
SERVICES = {
    "makima":      "makima.service",
    "deckery-hud": "deckery-hud.service",
}

# Human-readable display names for the menu
DISPLAY = {
    "makima":      "Deckery",
    "deckery-hud": "HUD",
}

# ── Pure state-routing functions (no GTK — fully testable) ───────────────────

def _tray_state(
    statuses: dict[str, str],
    paused: bool,
    steam_state: str,
    has_update: bool,
) -> str:
    """
    Return the tray icon priority key from combined system state.
    Result is one of: 'err', 'warn', 'update', 'ok'.
    Priority (highest first): err > warn > update > ok.
    No GTK dependency — call this in unit tests directly.
    """
    any_failed = any(s == "failed" for s in statuses.values())
    any_down   = any(s != "active" for s in statuses.values())
    steam_err  = steam_state == "overwritten"
    steam_warn = steam_state in ("unlocked", "no_source")

    if any_failed or steam_err:
        return "err"
    if any_down or paused or steam_warn:
        return "warn"
    if has_update:
        return "update"
    return "ok"


def _steam_item_state(steam_state: str) -> tuple[str, bool]:
    """
    Return (dot_key, unlock_sensitive) for a given SteamConfigWatcher state.
      dot_key:          'ok' | 'warn' | 'err' | 'grey'
      unlock_sensitive: True only when the file is locked (user can unlock it)
    No GTK dependency.
    """
    dot_key = {
        "locked":      "ok",
        "unlocked":    "warn",
        "overwritten": "err",
        "no_source":   "warn",
    }.get(steam_state, "grey")
    return dot_key, steam_state == "locked"


def _steam_click_action(steam_state: str) -> str | None:
    """
    Return the terminal action to open when the steam status item is clicked.
    Returns 'fix_and_lock', 'lock', or None (no-op).
    No GTK dependency.
    """
    return {"overwritten": "fix_and_lock", "unlocked": "lock"}.get(steam_state)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_pb(path: str, size: int = 16) -> GdkPixbuf.Pixbuf | None:
    """Load an SVG as a GdkPixbuf at the given pixel size. Returns None on failure."""
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
    except Exception:
        return None


def _icon_item(label: str, icon_name: str) -> Gtk.ImageMenuItem:
    """Create a Gtk.ImageMenuItem with a named theme icon."""
    item = Gtk.ImageMenuItem(label=label)
    img = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
    item.set_image(img)
    item.set_always_show_image(True)
    return item

# ── IPC / Service control ─────────────────────────────────────────────────────

def _makima_ipc(cmd: str) -> None:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            s.connect(_MAKIMA_SOCK)
            s.sendall((cmd + "\n").encode())
    except Exception:
        pass


def _service_status(unit: str) -> str:
    """Returns 'active', 'inactive', 'failed', or 'unknown'."""
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", unit],
            capture_output=True, text=True, timeout=2,
        )
        return r.stdout.strip()
    except Exception:
        return "unknown"


def _makima_paused() -> bool:
    try:
        with open(_STATE_JSON) as f:
            state = json.load(f)
        return bool(state.get("context", {}).get("paused", False))
    except Exception:
        return False


def _service_ctrl(action: str, unit: str) -> None:
    subprocess.Popen(["systemctl", "--user", action, unit])


def _open_dir(path: str) -> None:
    subprocess.Popen(["xdg-open", path])


def _open_url(url: str) -> None:
    subprocess.Popen(["xdg-open", url])


def _hud_dbus(method: str) -> None:
    """Call a method on the deckery-hud D-Bus interface. Silently ignores errors."""
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            _HUD_BUS, _HUD_PATH, _HUD_BUS, None,
        )
        proxy.call_sync(method, None, Gio.DBusCallFlags.NONE, 2000, None)
    except Exception:
        pass

# ── Tray App ──────────────────────────────────────────────────────────────────

class DeckeryTray:
    def __init__(self):
        # ── Status dot pixbufs for menu (12 px circles, no D-pad shape) ──
        self._pb = {
            "ok":   _load_pb(_DOT_OK,       12),
            "warn": _load_pb(_DOT_PAUSED,   12),
            "err":  _load_pb(_DOT_ERR,      12),
            "grey": _load_pb(_DOT_INACTIVE, 12),
        }

        self._indicator = AyatanaAppIndicator3.Indicator.new(
            "deckery-tray",
            _ICON_OK,
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        self._indicator.set_title("Deckery")

        self._menu             = Gtk.Menu()
        self._items            = {}
        self._statuses: dict   = {}   # last known service statuses from poll
        self._paused           = False
        self._poll_running     = False
        self._state_timeout_id = None
        self._updater          = Updater(on_state_change=self._on_update_state_changed)
        self._steam_watcher    = SteamConfigWatcher(on_state_change=self._on_steam_state_changed)

        self._build_menu()
        self._indicator.set_menu(self._menu)

        self._poll()
        GLib.timeout_add(POLL_MS, self._poll)
        self._watch_state_file()

    # ── Menu construction ─────────────────────────────────────────────────────

    def _status_item(self, name: str) -> Gtk.MenuItem:
        """Create a service-status MenuItem with icon + label in an HBox.
        Uses explicit Box child so label updates via set_text() are reliable
        (Gtk.ImageMenuItem.set_label() cannot update its AccelLabel when the
        child is an HBox)."""
        item = Gtk.MenuItem()
        box  = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        img  = Gtk.Image.new_from_pixbuf(self._pb["grey"])
        lbl  = Gtk.Label(label=f"{name}: …", xalign=0)
        box.pack_start(img, False, False, 0)
        box.pack_start(lbl, True,  True,  0)
        box.show_all()
        item.add(box)
        self._items[f"status_{name}"]     = item
        self._items[f"status_{name}_img"] = img
        self._items[f"status_{name}_lbl"] = lbl
        return item

    def _dynamic(self, item: Gtk.Widget) -> Gtk.Widget:
        """Mark an item as dynamic (hide/show via _poll, resist show_all)."""
        item.set_no_show_all(True)
        return item

    def _build_menu(self):
        m = self._menu

        # ── Header ────────────────────────────────────────────────────────
        _v = local_version()
        header = Gtk.MenuItem(label=_version_label(_v))
        header.set_sensitive(False)
        self._items["header"] = header
        m.append(header)
        m.append(Gtk.SeparatorMenuItem())

        # ── Deckery (Makima) ──────────────────────────────────────────────
        m.append(self._status_item("makima"))

        pause_item   = self._dynamic(_icon_item("Pause Deckery",   "media-playback-pause"))
        resume_item  = self._dynamic(_icon_item("Resume Deckery",  "media-playback-start"))
        restart_item = self._dynamic(_icon_item("Restart Deckery", "view-refresh"))
        start_item   = self._dynamic(_icon_item("Start Deckery",   "system-run"))
        stop_item    = self._dynamic(_icon_item("Stop Deckery",    "media-playback-stop"))

        pause_item  .connect("activate", self._on_pause)
        resume_item .connect("activate", self._on_resume)
        restart_item.connect("activate", lambda _: _service_ctrl("restart", "makima.service"))
        start_item  .connect("activate", lambda _: _service_ctrl("start",   "makima.service"))
        stop_item   .connect("activate", lambda _: _service_ctrl("stop",    "makima.service"))

        self._items["pause"]   = pause_item
        self._items["resume"]  = resume_item
        self._items["restart"] = restart_item
        self._items["start"]   = start_item
        self._items["stop"]    = stop_item

        for item in (pause_item, resume_item, restart_item, start_item, stop_item):
            m.append(item)
        m.append(Gtk.SeparatorMenuItem())

        # ── HUD ───────────────────────────────────────────────────────────
        hud_status = self._status_item("deckery-hud")
        hud_status.connect("activate", lambda _: _hud_dbus("Toggle"))
        m.append(hud_status)

        hud_restart = _icon_item("Restart HUD", "view-refresh")
        hud_restart.connect("activate", lambda _: _service_ctrl("restart", "deckery-hud.service"))
        m.append(hud_restart)

        osd_item = Gtk.CheckMenuItem(label="Onscreen Display")
        osd_item.set_active(True)
        osd_item.connect("toggled", self._on_osd_toggle)
        self._items["osd"] = osd_item
        m.append(osd_item)
        m.append(Gtk.SeparatorMenuItem())

        # ── Steam Config ──────────────────────────────────────────────────
        steam_status = self._status_item("steam-config")
        steam_status.connect("activate", self._on_steam_status_clicked)
        m.append(steam_status)

        unlock_item = _icon_item("Unlock for Steam update", "object-unlocked")
        unlock_item.connect("activate", lambda _: self._steam_watcher.open_unlock_terminal())
        self._items["steam-unlock"] = unlock_item
        m.append(unlock_item)
        m.append(Gtk.SeparatorMenuItem())

        # ── Config / Updates ──────────────────────────────────────────────
        cfg_item = _icon_item("Open config folder", "folder")
        cfg_item.connect("activate", lambda _: _open_dir(_CONFIG_DIR))
        m.append(cfg_item)

        upd_item = _icon_item(self._updater.label, "system-software-update")
        upd_item.set_sensitive(self._updater.sensitive)
        upd_item.connect("activate", self._on_update_clicked)
        self._items["update"] = upd_item
        m.append(upd_item)
        m.append(Gtk.SeparatorMenuItem())

        # ── Community links ───────────────────────────────────────────────
        bug_item  = _icon_item("Report a Bug",      "tools-report-bug")
        feat_item = _icon_item("Propose a Feature", "starred")
        bug_item .connect("activate", lambda _: _open_url(_GITHUB_DISCUSSIONS))
        feat_item.connect("activate", lambda _: _open_url(_GITHUB_DISCUSSIONS))
        m.append(bug_item)
        m.append(feat_item)
        m.append(Gtk.SeparatorMenuItem())

        # ── Quit ──────────────────────────────────────────────────────────
        quit_item = _icon_item("Quit Deckery", "application-exit")
        quit_item.connect("activate", self._on_quit)
        m.append(quit_item)

        m.show_all()
        # Dynamic items start hidden; _poll() sets their visibility on first run.

    # ── State-file watcher ────────────────────────────────────────────────────

    def _watch_state_file(self):
        f = Gio.File.new_for_path(_STATE_JSON)
        self._monitor = f.monitor_file(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self._monitor.connect("changed", self._on_state_changed)

    def _on_state_changed(self, _monitor, _file, _other, event):
        if event not in (Gio.FileMonitorEvent.CHANGED,
                         Gio.FileMonitorEvent.CREATED,
                         Gio.FileMonitorEvent.RENAMED):
            return
        if self._state_timeout_id:
            GLib.source_remove(self._state_timeout_id)
        self._state_timeout_id = GLib.timeout_add(120, self._on_state_debounced)

    def _on_state_debounced(self):
        self._state_timeout_id = None
        self._poll()
        return GLib.SOURCE_REMOVE

    # ── Polling ───────────────────────────────────────────────────────────────

    def _poll(self) -> bool:
        if self._poll_running:
            return GLib.SOURCE_CONTINUE
        self._poll_running = True
        threading.Thread(target=self._poll_thread, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _poll_thread(self):
        statuses = {name: _service_status(unit) for name, unit in SERVICES.items()}
        paused   = _makima_paused()
        GLib.idle_add(self._apply_poll, statuses, paused)

    def _apply_poll(self, statuses: dict, paused: bool):
        self._poll_running = False
        self._paused   = paused
        self._statuses = statuses

        # ── Update service status icons + labels ──────────────────────────
        for name, status in statuses.items():
            if name == "makima" and status == "active" and paused:
                pb_key  = "warn"
                display = "paused"
            elif status == "active":
                pb_key  = "ok"
                display = "active"
            elif status in ("inactive", "unknown"):
                pb_key  = "grey"
                display = status
            else:
                pb_key  = "err"
                display = status
            pb = self._pb.get(pb_key)
            if pb:
                self._items[f"status_{name}_img"].set_from_pixbuf(pb)
            self._items[f"status_{name}_lbl"].set_text(f"{DISPLAY.get(name, name)}: {display}")

        # ── Update steam config item ──────────────────────────────────────
        self._refresh_steam_item()

        # ── Makima control visibility ─────────────────────────────────────
        makima_active = statuses.get("makima", "unknown") == "active"
        self._items["pause"]  .set_visible(makima_active and not paused)
        self._items["resume"] .set_visible(makima_active and paused)
        self._items["restart"].set_visible(makima_active and paused)
        self._items["start"]  .set_visible(not makima_active)
        self._items["stop"]   .set_visible(makima_active and not paused)

        # ── Tray icon ─────────────────────────────────────────────────────
        self._refresh_tray_icon()

        return GLib.SOURCE_REMOVE

    # ── Tray icon ─────────────────────────────────────────────────────────────

    def _refresh_tray_icon(self) -> None:
        """Update the tray icon based on all current states."""
        key = _tray_state(
            self._statuses,
            self._paused,
            self._steam_watcher.state,
            self._updater.state == UpdateState.UPDATE_AVAILABLE,
        )
        icon, tooltip = _TRAY_ICONS[key]
        self._indicator.set_icon_full(icon, tooltip)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_pause(self, _item):
        _makima_ipc("pause")
        GLib.timeout_add(300, self._poll)

    def _on_resume(self, _item):
        _makima_ipc("resume")
        GLib.timeout_add(300, self._poll)

    def _on_osd_toggle(self, _item):
        _hud_dbus("ToggleOsd")

    def _on_update_clicked(self, _item):
        self._updater.on_clicked()

    def _on_update_state_changed(self):
        """Called by Updater when its state changes."""
        item = self._items.get("update")
        if item:
            item.set_label(self._updater.label)
            item.set_sensitive(self._updater.sensitive)
        # Refresh header label — local_version() may have changed after an update
        header = self._items.get("header")
        if header:
            _v = local_version()
            header.set_label(_version_label(_v))
        self._refresh_tray_icon()
        return GLib.SOURCE_REMOVE

    def _on_steam_status_clicked(self, _item):
        action = _steam_click_action(self._steam_watcher.state)
        if action == "fix_and_lock":
            self._steam_watcher.open_fix_and_lock_terminal()
        elif action == "lock":
            self._steam_watcher.open_lock_terminal()

    def _on_steam_state_changed(self):
        """Called by SteamConfigWatcher when its state changes."""
        self._refresh_steam_item()
        self._refresh_tray_icon()
        return GLib.SOURCE_REMOVE

    def _refresh_steam_item(self) -> None:
        """Update the steam config status item in the menu."""
        state = self._steam_watcher.state
        dot_key, unlock_sensitive = _steam_item_state(state)
        pb     = self._pb.get(dot_key)
        img    = self._items.get("status_steam-config_img")
        lbl    = self._items.get("status_steam-config_lbl")
        unlock = self._items.get("steam-unlock")
        if img and pb:
            img.set_from_pixbuf(pb)
        if lbl:
            lbl.set_text(self._steam_watcher.label)
        if unlock:
            unlock.set_sensitive(unlock_sensitive)

    def _on_quit(self, _item):
        self._steam_watcher.stop()
        _service_ctrl("stop", "makima.service")
        _service_ctrl("stop", "deckery-hud.service")
        Gtk.main_quit()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(name)s: %(levelname)s: %(message)s",
    )
    DeckeryTray()
    Gtk.main()
