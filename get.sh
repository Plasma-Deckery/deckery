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
    # Capture current version BEFORE checkout so install.sh can roll back to it.
    export DECKERY_PREV_TAG="$(git -C "$DECKERY_DIR" describe --tags --exact-match HEAD 2>/dev/null || true)"

    echo "deckery: fetching..."
    # --force so re-tagged releases overwrite stale local refs
    git -C "$DECKERY_DIR" fetch origin --tags --force
fi

# Find the latest release tag by version sort — works regardless of HEAD position
# (describe --abbrev=0 fails when repo is left in detached HEAD from a prior update).
LATEST_TAG="$(git -C "$DECKERY_DIR" tag --sort=-version:refname | head -1)"
if [ -n "$LATEST_TAG" ]; then
    echo "Checking out latest release: $LATEST_TAG"
    git -C "$DECKERY_DIR" checkout --force "$LATEST_TAG"
else
    echo "No release tag found — running from main (development mode)"
    git -C "$DECKERY_DIR" checkout --force main
fi

export DECKERY_RELEASE_TAG="$LATEST_TAG"
bash "$DECKERY_DIR/install.sh"
