#!/usr/bin/env python3
"""
controller-route — system tray to route the Steam Deck controller
(USB 28de:1205) between the host and any running QEMU VM.

Usage:
    python3 controller-route.py

Requires: python-gobject, libayatana-appindicator (gtk3 variant)
"""

import os
import re
import socket
import subprocess
import sys

import gi
gi.require_version("Gtk", "3.0")
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3
    HAS_INDICATOR = True
except (ValueError, ImportError):
    HAS_INDICATOR = False

from gi.repository import Gtk, GLib

# ── USB identity of the Steam Deck controller ─────────────────────────────────
VENDOR_ID  = "0x28de"
PRODUCT_ID = "0x1205"
DEVICE_ID  = "steamctrl"   # stable QEMU device id
BUS        = "xhci.0"


# ── QEMU monitor helpers ──────────────────────────────────────────────────────

def _qemu_send(sock_path: str, cmd: str) -> str:
    """Send one HMP command to a QEMU monitor socket, return raw response."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(sock_path)
            # drain initial banner / prompt
            buf = b""
            while b"(qemu)" not in buf:
                buf += s.recv(4096)
            s.sendall((cmd + "\n").encode())
            resp = b""
            try:
                while b"(qemu)" not in resp:
                    resp += s.recv(4096)
            except OSError:
                pass
            return resp.decode(errors="replace")
    except Exception as exc:
        return f"ERROR: {exc}"


def _controller_in_vm(sock_path: str) -> bool:
    return DEVICE_ID in _qemu_send(sock_path, "info usb")


def _attach(sock_path: str) -> None:
    _qemu_send(
        sock_path,
        f"device_add usb-host,bus={BUS},"
        f"vendorid={VENDOR_ID},productid={PRODUCT_ID},id={DEVICE_ID}",
    )


def _detach(sock_path: str) -> None:
    _qemu_send(sock_path, f"device_del {DEVICE_ID}")


# ── VM discovery ──────────────────────────────────────────────────────────────

def find_vms() -> list[tuple[str, str]]:
    """Return [(name, monitor_sock_path), ...] for every live QEMU process."""
    try:
        out = subprocess.check_output(["pgrep", "-a", "qemu-system"], text=True)
    except subprocess.CalledProcessError:
        return []
    vms = []
    for line in out.strip().splitlines():
        m_name = re.search(r"-name\s+(\S+)", line)
        name   = m_name.group(1) if m_name else "QEMU"
        m_sock = re.search(r"-monitor\s+unix:([^,\s]+)", line)
        if not m_sock:
            continue
        sock = m_sock.group(1)
        if os.path.exists(sock):
            vms.append((name, sock))
    return vms


def controller_present() -> bool:
    try:
        return b"28de:1205" in subprocess.check_output(["lsusb"])
    except Exception:
        return False


def current_vm(vms: list) -> str | None:
    """sock_path of the VM that currently holds the controller, or None (= host)."""
    for _name, sock in vms:
        if _controller_in_vm(sock):
            return sock
    return None


# ── Tray ─────────────────────────────────────────────────────────────────────

class ControllerRouteTray:
    def __init__(self) -> None:
        self._menu = Gtk.Menu()

        if HAS_INDICATOR:
            self._ind = AppIndicator3.Indicator.new(
                "controller-route",
                "input-gaming",
                AppIndicator3.IndicatorCategory.HARDWARE,
            )
            self._ind.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self._ind.set_title("Controller Route")
            self._ind.set_menu(self._menu)
        else:
            # Fallback: StatusIcon (deprecated but always present)
            self._si = Gtk.StatusIcon()
            self._si.set_from_icon_name("input-gaming")
            self._si.set_tooltip_text("Controller Route")
            self._si.connect("popup-menu", self._on_popup)
            self._si.set_visible(True)

        self._refresh_menu()
        GLib.timeout_add_seconds(3, self._tick)

    # ── popup for StatusIcon fallback ─────────────────────────────────────────
    def _on_popup(self, icon, button, time):
        self._menu.popup(None, None, Gtk.StatusIcon.position_menu,
                         icon, button, time)

    # ── periodic refresh ──────────────────────────────────────────────────────
    def _tick(self) -> bool:
        self._refresh_menu()
        return True

    # ── build / rebuild menu ──────────────────────────────────────────────────
    def _refresh_menu(self) -> None:
        for child in self._menu.get_children():
            self._menu.remove(child)

        vms        = find_vms()
        present    = controller_present()
        active_sock = current_vm(vms) if present else None   # None = host has it

        # ── header ────────────────────────────────────────────────────────────
        if not present:
            hdr = Gtk.MenuItem(label="⚠ Controller nicht gefunden")
            hdr.set_sensitive(False)
            self._menu.append(hdr)
        else:
            hdr = Gtk.MenuItem(label="Controller routen zu:")
            hdr.set_sensitive(False)
            self._menu.append(hdr)

        self._menu.append(Gtk.SeparatorMenuItem())

        # ── Host entry ────────────────────────────────────────────────────────
        host_active = present and active_sock is None
        host_item   = Gtk.MenuItem(label=("✓ Host" if host_active else "Host"))
        host_item.set_sensitive(present and not host_active)
        host_item.connect("activate", self._to_host, vms)
        self._menu.append(host_item)

        # ── one entry per VM ──────────────────────────────────────────────────
        for name, sock in vms:
            is_active = (sock == active_sock)
            label     = f"✓ {name}" if is_active else name
            item      = Gtk.MenuItem(label=label)
            item.set_sensitive(present and not is_active)
            item.connect("activate", self._to_vm, sock, vms, active_sock)
            self._menu.append(item)

        self._menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Beenden")
        quit_item.connect("activate", lambda _: Gtk.main_quit())
        self._menu.append(quit_item)

        self._menu.show_all()

        # update indicator label / tooltip
        if HAS_INDICATOR:
            if not present:
                self._ind.set_title("Controller: nicht gefunden")
            elif host_active:
                self._ind.set_title("Controller → Host")
            else:
                vm_name = next((n for n, s in vms if s == active_sock), "VM")
                self._ind.set_title(f"Controller → {vm_name}")

    # ── routing actions ───────────────────────────────────────────────────────
    def _to_host(self, _item, vms):
        for _name, sock in vms:
            if _controller_in_vm(sock):
                _detach(sock)
        self._refresh_menu()

    def _to_vm(self, _item, target_sock, vms, current_sock):
        if current_sock:
            _detach(current_sock)
        _attach(target_sock)
        self._refresh_menu()


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not HAS_INDICATOR:
        print("libayatana-appindicator nicht gefunden — StatusIcon Fallback aktiv",
              file=sys.stderr)
    ControllerRouteTray()
    Gtk.main()


if __name__ == "__main__":
    main()
