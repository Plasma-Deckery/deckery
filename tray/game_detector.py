"""
game_detector.py — Detect whether a Steam game is running in Desktop Mode.

Architecture
------------
Mirrors the approach in makima's kwin_watcher.rs:

1. We register a D-Bus service "org.deckery.watcher" and expose
   the object /watcher with method WindowActivated(class_name).
2. We write a tiny KWin script to /tmp and load it via
   org.kde.kwin.Scripting.loadScript / .start().
3. Whenever KWin fires workspace.windowActivated, the script calls
   back into WindowActivated → we run detect() and log the result.

detect() uses psutil to walk the process tree: a Steam "reaper" process
with live children means a game is running.

This module is currently logging-only — no IPC to makima yet. The goal
is to verify on-device that both the KWin callback and the process
detection produce correct results before wiring into the control flow.

Usage (standalone)
------------------
    python3 game_detector.py        # runs GLib main loop, logs to stderr
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

import psutil
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Gio, GLib, Notify

log = logging.getLogger(__name__)

_notify_handle: Notify.Notification | None = None

def _notify(summary: str, body: str, icon: str = "dialog-information") -> None:
    """Show or replace a desktop notification (reuses a single handle to avoid stacking)."""
    global _notify_handle
    try:
        if _notify_handle is None:
            _notify_handle = Notify.Notification.new(summary, body, icon)
        else:
            _notify_handle.update(summary, body, icon)
        _notify_handle.show()
    except Exception as e:
        log.debug("[game_detector] notification failed: %s", e)

# ── KWin script ────────────────────────────────────────────────────────────────
# Injected into KWin via org.kde.kwin.Scripting. On every window-activation
# change KWin calls back into our D-Bus method WindowActivated(class_name).

_KWIN_SCRIPT = """\
workspace.windowActivated.connect(function(w) {
    var cls = (w && w.resourceClass) ? w.resourceClass : "";
    var cap = (w && w.caption) ? w.caption : "";
    if (cls === "steam" && (cap.indexOf("Big Picture") !== -1 || cap.indexOf("Big-Picture") !== -1)) {
        cls = "steam-bpm";
    }
    callDBus("org.deckery.watcher", "/watcher", "org.deckery.watcher", "WindowActivated", cls);
});
"""

_SCRIPT_PATH  = "/tmp/deckery-kwin-watcher.js"
_PLUGIN_NAME  = "deckery-watcher"
_BUS_NAME     = "org.deckery.watcher"
_OBJECT_PATH  = "/watcher"
_INTERFACE    = "org.deckery.watcher"

_IFACE_XML = f"""\
<node>
  <interface name="{_INTERFACE}">
    <method name="WindowActivated">
      <arg type="s" name="class_name" direction="in"/>
    </method>
  </interface>
</node>"""


# ── Process detection (psutil) ────────────────────────────────────────────────

@dataclass
class DetectionResult:
    game_running: bool
    steam_pid:    int | None
    reapers:      list[dict] = field(default_factory=list)
    notes:        list[str]  = field(default_factory=list)


def _find_steam() -> psutil.Process | None:
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            if proc.info["name"] == "steam" and any(
                "steam" in (arg or "").lower()
                for arg in (proc.info["cmdline"] or [])
            ):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def _steam_in_ancestors(proc: psutil.Process) -> bool:
    try:
        return any(p.name() == "steam" for p in proc.parents())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def detect() -> DetectionResult:
    """Walk the process tree and report whether a Steam game is running."""
    result = DetectionResult(game_running=False, steam_pid=None)

    steam = _find_steam()
    if steam is None:
        result.notes.append("Steam process not found")
        return result

    result.steam_pid = steam.pid
    result.notes.append(f"Steam client PID: {steam.pid}")

    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] != "reaper":
                continue
            if not _steam_in_ancestors(proc):
                continue
            game_procs  = proc.children()
            child_names = [c.name() for c in game_procs]
            entry = {
                "reaper_pid":   proc.pid,
                "reaper_cmd":   " ".join(proc.cmdline())[:120],
                "children":     child_names,
                "has_children": bool(game_procs),
            }
            result.reapers.append(entry)
            if game_procs:
                result.game_running = True
                result.notes.append(
                    f"Reaper {proc.pid} has children: {child_names} → game running"
                )
            else:
                result.notes.append(
                    f"Reaper {proc.pid} has no children (starting up or shutting down)"
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not result.reapers:
        result.notes.append("No Steam reaper processes found — no game running")
    return result


def log_result(result: DetectionResult, effective_running: bool | None = None) -> None:
    # Use effective_running (which includes BPM) if provided, else fall back to psutil result.
    running = effective_running if effective_running is not None else result.game_running
    status = "GAME RUNNING" if running else "no game"
    log.info("[game_detector] %-14s  steam=%s  reapers=%d",
             status, result.steam_pid or "—", len(result.reapers))
    for note in result.notes:
        log.debug("[game_detector]   %s", note)
    for r in result.reapers:
        log.debug("[game_detector]   reaper %d  children=%s",
                  r["reaper_pid"], r["children"])


# ── KWin watcher ──────────────────────────────────────────────────────────────

class KWinGameWatcher:
    """
    Registers a KWin script and a D-Bus callback object.
    On every window-activation event, runs detect() and logs the result.
    Optionally calls on_change(game_running: bool) when state changes.
    """

    def __init__(self, on_change=None):
        self._on_change    = on_change
        self._conn         = None
        self._reg_id       = None
        self._game_state   = None   # last known state, None = unknown
        self._last_class   = None   # last non-empty window class we notified about

    def start(self) -> bool:
        """
        Register D-Bus object and load KWin script.
        Returns True on success, False if KWin scripting is unavailable.
        """
        try:
            self._conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except Exception as e:
            log.error("[game_detector] session bus unavailable: %s", e)
            return False

        # Register our D-Bus object so KWin can call back into us.
        node_info = Gio.DBusNodeInfo.new_for_xml(_IFACE_XML)
        self._reg_id = self._conn.register_object_with_closures2(
            _OBJECT_PATH,
            node_info.interfaces[0],
            self._on_method_call,   # method_call_closure
            None,                   # get_property_closure
            None,                   # set_property_closure
        )

        # Request the bus name.
        try:
            self._conn.call_sync(
                "org.freedesktop.DBus", "/org/freedesktop/DBus",
                "org.freedesktop.DBus", "RequestName",
                GLib.Variant("(su)", (_BUS_NAME, 0)),
                GLib.VariantType("(u)"),
                Gio.DBusCallFlags.NONE, -1, None,
            )
        except Exception as e:
            log.error("[game_detector] could not acquire bus name %s: %s", _BUS_NAME, e)
            return False

        # Write the KWin script, force-unload any previous instance, then load fresh.
        try:
            with open(_SCRIPT_PATH, "w") as f:
                f.write(_KWIN_SCRIPT)
            # Unload silently — may return False if not loaded, that's fine.
            try:
                self._conn.call_sync(
                    "org.kde.KWin", "/Scripting",
                    "org.kde.kwin.Scripting", "unloadScript",
                    GLib.Variant("(s)", (_PLUGIN_NAME,)),
                    None, Gio.DBusCallFlags.NONE, -1, None,
                )
                log.debug("[game_detector] unloaded previous KWin script")
            except Exception:
                pass
            self._conn.call_sync(
                "org.kde.KWin", "/Scripting",
                "org.kde.kwin.Scripting", "loadScript",
                GLib.Variant("(ss)", (_SCRIPT_PATH, _PLUGIN_NAME)),
                None, Gio.DBusCallFlags.NONE, -1, None,
            )
            self._conn.call_sync(
                "org.kde.KWin", "/Scripting",
                "org.kde.kwin.Scripting", "start",
                None, None, Gio.DBusCallFlags.NONE, -1, None,
            )
        except Exception as e:
            log.error("[game_detector] could not load KWin script: %s", e)
            return False

        log.info("[game_detector] KWin watcher active — waiting for focus events")

        # Run an initial detection so we catch a game that was already running
        # when the watcher started.
        self._check()
        return True

    def stop(self) -> None:
        if self._conn and self._reg_id:
            self._conn.unregister_object(self._reg_id)
        try:
            if self._conn:
                self._conn.call_sync(
                    "org.kde.KWin", "/Scripting",
                    "org.kde.kwin.Scripting", "unloadScript",
                    GLib.Variant("(s)", (_PLUGIN_NAME,)),
                    None, Gio.DBusCallFlags.NONE, -1, None,
                )
        except Exception:
            pass

    # ── internal ──────────────────────────────────────────────────────────────

    def _on_method_call(self, connection, sender, path, interface,
                        method, params, invocation):
        if method == "WindowActivated":
            class_name = params[0] if params else ""
            log.debug("[game_detector] focus → %r", class_name)
            self._check(class_name)
        invocation.return_value(None)

    def _check(self, class_name: str = "") -> None:
        t0 = time.perf_counter()
        result = detect()

        # Two independent signals can trigger gaming mode:
        #   1. psutil: a Steam reaper process has live children → a game is running
        #   2. KWin caption: the focused window is Steam Big Picture Mode ("steam-bpm")
        #      Regular Steam desktop client (caption "Steam") does NOT count.
        steam_focused = class_name == "steam-bpm"
        effective_running = result.game_running or steam_focused
        elapsed_ms = (time.perf_counter() - t0) * 1000
        log_result(result, effective_running)
        log.info("[game_detector] detection took %.1f ms", elapsed_ms)

        if class_name and class_name != self._last_class:
            self._last_class = class_name
            if effective_running:
                _notify(
                    f"Focus: {class_name}",
                    "Steam active — gaming mode",
                    "media-playback-start",
                )
            else:
                _notify(
                    f"Focus: {class_name}",
                    "Not a Steam game",
                    "application-x-executable",
                )

        if effective_running != self._game_state:
            self._game_state = effective_running
            if self._on_change:
                self._on_change(effective_running)


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    Notify.init("deckery-game-detector")

    def on_change(game_running: bool):
        log.info("[game_detector] *** STATE CHANGE → %s ***",
                 "GAME RUNNING" if game_running else "no game")

    watcher = KWinGameWatcher(on_change=on_change)
    if not watcher.start():
        log.error("Failed to start watcher — is KWin running?")
        raise SystemExit(1)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        watcher.stop()
