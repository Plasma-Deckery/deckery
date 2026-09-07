#!/bin/bash
# redeploy-tray.sh — push the working tree's tray code into the installed copy
# and restart it. No sudo required.
#
# get.sh installs *releases*: it checks out the newest tag into
# ~/.local/share/deckery/deckery. That is right for users and wrong while
# developing, because the tray then runs whatever the last release contained,
# not what you just edited. This script closes that gap — it overwrites the
# installed tray/ with the working tree's and restarts the service.
#
# It deliberately copies only tray/. configs/ stays untouched (those are the
# user's own bindings) and systemd/ needs a daemon-reload, so unit changes are
# not something to do behind your back.
#
# Note this deploys the *working tree*, uncommitted changes included. That is
# the point, but it means `git status` is worth a glance first.

set -e
REPO="$(dirname "$(readlink -f "$0")")"
DEST="$HOME/.local/share/deckery/deckery"

if [ ! -d "$DEST" ]; then
    echo "Not installed: $DEST does not exist." >&2
    echo "Run get.sh first." >&2
    exit 1
fi

echo "Copying tray/ → $DEST/tray/"
cp -a "$REPO/tray/." "$DEST/tray/"

# Stale bytecode from the previous version shadows fresh sources often enough
# to be worth removing outright.
find "$DEST/tray" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

systemctl --user restart deckery-tray.service
echo "Done — deckery-tray restarted from the working tree."
