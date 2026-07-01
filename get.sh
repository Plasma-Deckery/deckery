#!/bin/bash
# get.sh — Deckery one-line installer entry point.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/Plasma-Deckery/deckery/main/get.sh | bash

set -e

DECKERY_DIR="$HOME/.local/share/deckery/deckery"

if [ ! -d "$DECKERY_DIR" ]; then
    echo "Cloning deckery..."
    mkdir -p "$(dirname "$DECKERY_DIR")"
    git clone https://github.com/Plasma-Deckery/deckery.git "$DECKERY_DIR"
else
    echo "deckery: pulling latest..."
    git -C "$DECKERY_DIR" fetch --tags
    git -C "$DECKERY_DIR" pull --ff-only || echo "  (skipped — local changes present)"
fi

# Check out the latest release tag so the installer runs in release mode.
# This ensures all sub-repos are pinned to the same tested version.
LATEST_TAG="$(git -C "$DECKERY_DIR" describe --tags --abbrev=0 2>/dev/null || true)"
if [ -n "$LATEST_TAG" ]; then
    echo "Checking out latest release: $LATEST_TAG"
    git -C "$DECKERY_DIR" checkout "$LATEST_TAG"
else
    echo "No release tag found — running from main (development mode)"
fi

export DECKERY_RELEASE_TAG="$LATEST_TAG"
bash "$DECKERY_DIR/install.sh"
