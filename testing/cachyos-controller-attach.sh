#!/bin/bash
# Pass the Steam Deck Controller (28de:1205) through to the CachyOS test VM.
# The host loses access while the VM holds the device.
# Use cachyos-controller-detach.sh to return it to the host.
#
# Requires: VM running with -device qemu-xhci,id=xhci (see cachyos-vm-start.sh)

SOCK="${VM_ROOT:-$HOME/VMs}/cachyos-test/monitor.sock"

if [ ! -S "$SOCK" ]; then
  echo "ERROR: VM not running (no monitor socket at $SOCK)"
  exit 1
fi

if ! lsusb | grep -q "28de:1205"; then
  echo "ERROR: Steam Controller not found on host"
  exit 1
fi

USB_INFO=$(echo "info usb" | socat - "$SOCK" 2>/dev/null)
if echo "$USB_INFO" | grep -q "steamctrl"; then
  echo "Controller is already in the VM"
  exit 0
fi

echo "device_add usb-host,bus=xhci.0,vendorid=0x28de,productid=0x1205,id=steamctrl" \
  | socat - "$SOCK" > /dev/null 2>&1

sleep 1
USB_INFO=$(echo "info usb" | socat - "$SOCK" 2>/dev/null)
if echo "$USB_INFO" | grep -q "steamctrl"; then
  echo "✓ Controller → CachyOS VM (host no longer has access)"
else
  echo "ERROR: Failed to attach controller to VM"
  exit 1
fi
