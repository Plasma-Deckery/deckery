#!/bin/bash
# First boot of the Pizzarchy test VM: boots the installer ISO with the empty
# target disk attached. The installer is controller-only — route the Steam
# Controller in with pizzarchy-controller-attach.sh (or the controller-route.py
# tray) once QEMU's display window is up.
#
# Run pizzarchy-vm-start.sh instead for every boot after the install finishes.
#
# No zoom-to-fit: it dropped the display permanently blank after a window
# resize on this host (GTK/virtio-vga), forcing a hard restart mid-install.
# Plain `-display gtk` scales less smoothly but doesn't lose the framebuffer.
#
# The disk is attached as an emulated NVMe device (not virtio) because the
# installer (deck-form.sh) only accepts /dev/nvme0n1 or /dev/mmcblk0 as an
# install target — a virtio-blk disk shows up as /dev/vda and is refused as
# "no eligible install disk".
#
# SMBIOS is spoofed as a Galileo/Valve (Steam Deck OLED) machine because
# omarchy-deck-early's wipe gate (deck_early_require_oled) checks
# /sys/class/dmi/id/product_name == Galileo and sys_vendor contains Valve
# before it will touch a disk at all — even one that passed the drive
# picker. Without this, selecting the disk bounces straight back to "no
# eligible install disk was found". This is exactly what Pizzarchy's own
# QEMU test harness does (test/vm/*.sh) — there is deliberately no bypass.
#
# If install-disk.qcow2 doesn't exist yet, this script creates it blank and
# boots the installer straight away — no competing bootable OS on it yet,
# so `-boot order=d` reliably lands on the CD-ROM.
#
# If install-disk.qcow2 already exists, this script REFUSES to touch it —
# it no longer wipes on every run. A finished (or in-progress) install must
# never be silently destroyed just because this script got run again, by a
# person or an agent that didn't know a real install was sitting there. Set
# PIZZARCHY_FORCE_REINSTALL=yes to explicitly wipe and reinstall from
# scratch. For every normal boot after install, use pizzarchy-vm-start.sh
# instead — it never touches the disk.
#
# Using the stable v2026.09.20 release, not the Fast-Install prerelease: the
# Fast-Install build's own choice-file check (see deck-install-invocation.patch)
# crashes every interactive/controller-driven install with "cidata drive
# carries no 'preinstalls' file" — confirmed absent from this release by
# checking the file doesn't exist at this tag. This release DOES require
# real internet during install (Steam is downloaded from Valve as part of
# setup) — QEMU's user-mode networking (-net user below) provides that via
# NAT/DHCP already, no extra config needed.
#
# Requirements: qemu-system-x86_64, OVMF (edk2-ovmf), KVM
#
# smp 2 / m 4G, not 4/8G: the host here IS the physical Steam Deck (8 threads,
# ~15G usable) also running the desktop and this Claude session — handing an
# installer half of everything made the whole handheld crawl. 2 vCPUs/4G is
# plenty for an Arch-based interactive install.
#
# Set VM_ROOT to keep the VM images somewhere other than ~/VMs.
# Set PIZZARCHY_ISO to override the installer ISO path.
#
# The serial console is exposed as a unix socket for live use (socat) AND
# mirrored to $VMDIR/serial.log (logfile=/logappend=on on the chardev) — a
# prior VM that got killed for hogging the host left zero guest-side trace
# once the process died, since a bare socket has no scrollback. The log file
# survives the process.

VMDIR="${VM_ROOT:-$HOME/VMs}/pizzarchy-test"
ISO="${PIZZARCHY_ISO:-/run/media/$USER/Ventoy/Boot ISOs/pizzarchy-omarchy-4.0.4-2026-09-20-x86_64.iso}"
OVMF_VARS_TEMPLATE=/usr/share/edk2/ovmf/OVMF_VARS.fd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/ensure-controller-tray.sh"

if [ ! -f "$ISO" ]; then
  echo "ERROR: installer ISO not found at: $ISO"
  echo "Set PIZZARCHY_ISO to override."
  exit 1
fi

if [ -f "$VMDIR/install-disk.qcow2" ]; then
  if [ "${PIZZARCHY_FORCE_REINSTALL:-}" != "yes" ]; then
    echo "ERROR: $VMDIR/install-disk.qcow2 already exists — refusing to wipe it."
    echo "This looks like a finished or in-progress install. To boot it normally,"
    echo "use pizzarchy-vm-start.sh instead (it never touches the disk)."
    echo ""
    echo "To really wipe it and reinstall from scratch, rerun as:"
    echo "  PIZZARCHY_FORCE_REINSTALL=yes bash $0"
    exit 1
  fi
  echo "PIZZARCHY_FORCE_REINSTALL=yes set — wiping existing install-disk.qcow2 and UEFI NVRAM as requested."
else
  echo "No existing install-disk.qcow2 — creating a blank one."
fi

pkill -f "qemu-system.*$VMDIR/monitor\.sock" 2>/dev/null && sleep 1
rm -f "$VMDIR/monitor.sock" "$VMDIR/serial.sock"
rm -f "$VMDIR/install-disk.qcow2" "$VMDIR/OVMF_VARS.fd"
qemu-img create -f qcow2 "$VMDIR/install-disk.qcow2" 64G >/dev/null
cp "$OVMF_VARS_TEMPLATE" "$VMDIR/OVMF_VARS.fd"

setsid env GDK_BACKEND=x11 GDK_CORE_DEVICE_EVENTS=1 qemu-system-x86_64 \
  -enable-kvm -cpu host -smp 2 -m 4G \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file="$VMDIR/OVMF_VARS.fd" \
  -drive file="$VMDIR/install-disk.qcow2",format=qcow2,if=none,id=deckssd \
  -device nvme,drive=deckssd,serial=pizzarchydeck0 \
  -drive file="$ISO",format=raw,media=cdrom,if=ide \
  -boot order=d \
  -smbios type=1,manufacturer=Valve,product=Galileo,version=1 \
  -smbios type=2,manufacturer=Valve,product=Galileo \
  -net nic,model=virtio -net user,hostfwd=tcp::2226-:22 \
  -device virtio-vga \
  -device virtio-balloon-pci,free-page-reporting=on \
  -display gtk \
  -device qemu-xhci,id=xhci \
  -monitor unix:"$VMDIR/monitor.sock",server,nowait \
  -chardev socket,id=char-serial,path="$VMDIR/serial.sock",server=on,wait=off,logfile="$VMDIR/serial.log",logappend=on \
  -serial chardev:char-serial \
  -name "Pizzarchy-Install" > /tmp/pizzarchy-vm.log 2>&1 &

echo $! > /tmp/pizzarchy-vm.pid
echo "VM started (PID $(cat /tmp/pizzarchy-vm.pid)) — booting installer from ISO"
echo "Logs: tail -f /tmp/pizzarchy-vm.log"
echo ""
echo "Route the Steam Controller in now: bash testing/pizzarchy-controller-attach.sh"
echo "(or use the controller-route.py tray)"
echo ""
echo "The installer wipes the selected drive in the VM (only the virtual"
echo "install-disk.qcow2 exists here, so that's the only target it can pick)."
echo ""
echo "Once install finishes and you've powered off, switch to pizzarchy-vm-start.sh"
echo "for every later boot — it does not attach the ISO."
