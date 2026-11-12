#!/bin/bash
# Start the Pizzarchy test VM (Omarchy/Hyprland on Steam Deck OLED) from the
# already-installed disk, with GTK display and USB hotplug support.
# Controller passthrough is NOT active at start — use pizzarchy-controller-attach.sh.
#
# Run pizzarchy-install-start.sh once first to install onto install-disk.qcow2.
#
# The disk is attached as an emulated NVMe device (not virtio), and SMBIOS
# is spoofed as Galileo/Valve (Steam Deck OLED), matching
# pizzarchy-install-start.sh — see that script for why.
#
# Requirements: qemu-system-x86_64, OVMF (edk2-ovmf), KVM
#
# smp 2 / m 4G, not 4/8G: the host here IS the physical Steam Deck (8 threads,
# ~15G usable) also running the desktop and this Claude session — handing the
# VM half of everything made the whole handheld crawl. 2 vCPUs/4G is plenty
# for Omarchy/Hyprland once it's installed.
#
# Set VM_ROOT to keep the VM images somewhere other than ~/VMs.

VMDIR="${VM_ROOT:-$HOME/VMs}/pizzarchy-test"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$SCRIPT_DIR/ensure-controller-tray.sh"

pkill -f "qemu-system.*$VMDIR/monitor\.sock" 2>/dev/null && sleep 1
rm -f "$VMDIR/monitor.sock" "$VMDIR/serial.sock"

setsid env GDK_BACKEND=x11 GDK_CORE_DEVICE_EVENTS=1 qemu-system-x86_64 \
  -enable-kvm -cpu host -smp 2 -m 4G \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file="$VMDIR/OVMF_VARS.fd" \
  -drive file="$VMDIR/install-disk.qcow2",format=qcow2,if=none,id=deckssd \
  -device nvme,drive=deckssd,serial=pizzarchydeck0 \
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
  -name "Pizzarchy" > /tmp/pizzarchy-vm.log 2>&1 &

echo $! > /tmp/pizzarchy-vm.pid
echo "VM started (PID $(cat /tmp/pizzarchy-vm.pid))"
echo "SSH:  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no -o StrictHostKeyChecking=no -p 2226 <user>@localhost"
echo "Logs: tail -f /tmp/pizzarchy-vm.log"
