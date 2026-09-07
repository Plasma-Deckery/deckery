#!/bin/bash
# Return the Steam Deck Controller from the VM back to the host.

SOCK="${VM_ROOT:-$HOME/VMs}/bazzite-test/monitor.sock"

if [ ! -S "$SOCK" ]; then
  echo "ERROR: VM not running (no monitor socket at $SOCK)"
  exit 1
fi

USB_INFO=$(echo "info usb" | socat - "$SOCK" 2>/dev/null)
if ! echo "$USB_INFO" | grep -q "steamctrl"; then
  echo "Controller is not in the VM"
  exit 0
fi

echo "device_del steamctrl" | socat - "$SOCK" > /dev/null 2>&1

sleep 1
USB_INFO=$(echo "info usb" | socat - "$SOCK" 2>/dev/null)
if echo "$USB_INFO" | grep -q "steamctrl"; then
  echo "ERROR: Failed to remove controller from VM"
  exit 1
else
  echo "✓ Controller → host"
fi
