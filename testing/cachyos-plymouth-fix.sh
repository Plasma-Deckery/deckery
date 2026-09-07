#!/bin/bash
# After every CachyOS VM boot: kill plymouthd which hangs on virtio-vga.
#
# Bug: plymouth-quit.service always times out in the CachyOS VM.
# plymouthd holds the DRM device (virtio-vga), so KDE's kwin_wayland
# renders behind the Plymouth spinner. Killing plymouthd releases the
# device and the KDE desktop becomes visible in the GTK window.
#
# Safe to run even if Plymouth has already exited (pgrep returns nothing,
# kill gets no PIDs, no error).

SSH_ASKPASS="" SSH_ASKPASS_REQUIRE=never \
  ssh -i ~/.ssh/vm_key \
  -o StrictHostKeyChecking=no \
  -o PasswordAuthentication=no \
  -o BatchMode=yes \
  -p 2224 deck@localhost \
  'PIDS=$(pgrep plymouthd); if [ -n "$PIDS" ]; then sudo kill -9 $PIDS && echo "✓ plymouthd killed, KDE desktop now visible"; else echo "plymouthd not running (already done)"; fi'
