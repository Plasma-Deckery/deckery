#!/bin/bash
# Return the Steam Deck Controller from the CachyOS VM back to the host.

SOCK=/home/philipp/VMs/cachyos-test/monitor.sock

if [ ! -S "$SOCK" ]; then
  echo "ERROR: VM not running (no monitor socket at $SOCK)"
  exit 1
fi

USB_INFO=$(echo "info usb" | socat - "$SOCK" 2>/dev/null)
if ! echo "$USB_INFO" | grep -q "steamctrl"; then
  echo "Controller is not in the VM (already on host?)"
  exit 0
fi

echo "device_del steamctrl" | socat - "$SOCK" > /dev/null 2>&1
sleep 1
echo "✓ Controller → host"
