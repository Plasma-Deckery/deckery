#!/bin/bash
# Start the Bazzite 44 test VM with GTK display and USB hotplug support.
# Controller passthrough is NOT active at start — use controller-attach.sh to add it.
#
# Requirements: qemu-system-x86_64, OVMF (edk2-ovmf), KVM, virglrenderer
#
# Set VM_ROOT to keep the VM images somewhere other than ~/VMs.
#
# GPU: virtio-vga-gl with Venus Vulkan (blob+hostmem) — required for Gamescope session testing.

VMDIR="${VM_ROOT:-$HOME/VMs}/bazzite-test"

rm -f "$VMDIR/monitor.sock" "$VMDIR/serial.sock"

setsid env GDK_BACKEND=x11 GDK_CORE_DEVICE_EVENTS=1 qemu-system-x86_64 \
  -enable-kvm -cpu host -smp 4 -m 6G \
  -machine q35,memory-backend=mem \
  -object memory-backend-memfd,id=mem,size=6G,share=on \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/ovmf/OVMF_CODE.fd \
  -drive if=pflash,format=qcow2,file="$VMDIR/OVMF_VARS.qcow2" \
  -drive file="$VMDIR/install-disk.qcow2",format=qcow2,if=virtio \
  -net nic,model=virtio -net user,hostfwd=tcp::2222-:22 \
  -device virtio-vga-gl,blob=on,venus=on,hostmem=4G \
  -display gtk,gl=on,zoom-to-fit=on \
  -device qemu-xhci,id=xhci \
  -monitor unix:"$VMDIR/monitor.sock",server,nowait \
  -serial unix:"$VMDIR/serial.sock",server,nowait \
  -name "Bazzite 44" > /tmp/bazzite-vm.log 2>&1 &

echo $! > /tmp/bazzite-vm.pid
echo "VM started (PID $(cat /tmp/bazzite-vm.pid))"
echo "SSH:  ssh -i ~/.ssh/vm_key -o BatchMode=yes -o PasswordAuthentication=no -o StrictHostKeyChecking=no -p 2222 liveuser@localhost"
echo "Logs: tail -f /tmp/bazzite-vm.log"
