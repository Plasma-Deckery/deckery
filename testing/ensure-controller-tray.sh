#!/bin/bash
# Make sure the controller-route.py tray is running, starting it if not.
# Idempotent: safe to source/call from every *-vm-start.sh so the tray is
# always up whenever a VM is running, without ever spawning a second copy.

if pgrep -f "python3.*controller-route\.py" >/dev/null 2>&1; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
nohup python3 "$SCRIPT_DIR/controller-route.py" > /tmp/controller-route.log 2>&1 &
disown
echo "Controller-route tray started (PID $!)"
