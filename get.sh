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
    git -C "$DECKERY_DIR" pull --ff-only || echo "  (skipped — local changes present)"
fi

bash "$DECKERY_DIR/install.sh"
