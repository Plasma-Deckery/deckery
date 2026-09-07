#!/bin/bash
# Start the CachyOS Handheld test VM with GTK display and USB hotplug support.
# Controller passthrough is NOT active at start — use cachyos-controller-attach.sh.
#
# IMPORTANT: After boot, Plymouth always hangs (known CachyOS VM bug).
#   KDE is running behind it but the DRM device is held by plymouthd.
#   Run cachyos-plymouth-fix.sh (or the inline fix below) after SSH comes up.
#
# Requirements: qemu-system-x86_64, OVMF (edk2-ovmf), KVM
#
# Set VM_ROOT to keep the VM images somewhere other than ~/VMs.

VMDIR="${VM_ROOT:-$HOME/VMs}/cachyos-test"

# Kill any stale QEMU instance first — deleting socket files while an old
# QEMU is still running creates an FD/inode mismatch that breaks monitor access.
kill $(pgrep qemu-system) 2>/dev/null && sleep 1
rm -f "$VMDIR/monitor.sock" "$VMDIR/serial.sock"

setsid env GDK_BACKEND=x11 GDK_CORE_DEVICE_EVENTS=1 qemu-system-x86_64 \
  -enable-kvm -cpu host -smp 4 -m 8G \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file="$VMDIR/OVMF_VARS.fd" \
  -drive file="$VMDIR/install-disk.qcow2",format=qcow2,if=virtio \
  -net nic,model=virtio -net user,hostfwd=tcp::2224-:22 \
  -device virtio-vga \
  -display gtk,zoom-to-fit=on \
  -device qemu-xhci,id=xhci \
  -monitor unix:"$VMDIR/monitor.sock",server,nowait \
  -serial unix:"$VMDIR/serial.sock",server,nowait \
  -name "CachyOS" > /tmp/cachyos-vm.log 2>&1 &

echo $! > /tmp/cachyos-vm.pid
echo "VM started (PID $(cat /tmp/cachyos-vm.pid))"
echo "SSH:  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no -o StrictHostKeyChecking=no -p 2224 deck@localhost"
echo "Logs: tail -f /tmp/cachyos-vm.log"
echo ""
echo "After SSH is up, kill Plymouth: ssh ... 'sudo kill -9 \$(pgrep plymouthd)'"
