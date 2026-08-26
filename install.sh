#!/bin/bash
# install.sh — Deckery full-stack installer.
#
# Clones all required repos, sets up the distrobox container,
# builds and installs all services. Re-running is safe (idempotent).
#
# Usage (first install / update — always use get.sh for release pinning):
#   bash <(curl -sSL https://raw.githubusercontent.com/Plasma-Deckery/deckery/main/get.sh)

set -e

DECKERY_DIR="$(dirname "$(readlink -f "$0")")"
PARENT_DIR="$(dirname "$DECKERY_DIR")"


MAKIMA_DIR="$PARENT_DIR/makima-deckery"
HUD_DIR="$PARENT_DIR/deckery-hud"
BIN_DIR="$HOME/.local/bin"
CFG_DIR="$HOME/.config/deckery"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║         Deckery Installer            ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Detect release tag ────────────────────────────────────────────────────────
#
# If install.sh is running from a tagged release commit, all sub-repos are
# checked out at the matching tag. This guarantees that every component is
# from a tested, compatible set.
#
# If running from an untagged commit (development / main), sub-repos are
# cloned or updated to their latest main branch.

# DECKERY_RELEASE_TAG may be set by get.sh; fall back to git describe for
# direct invocations (e.g. manual update: cd repo && git checkout vX.Y.Z && bash install.sh)
RELEASE_TAG="${DECKERY_RELEASE_TAG:-$(git -C "$DECKERY_DIR" describe --tags --exact-match HEAD 2>/dev/null || true)}"

if [ -n "$RELEASE_TAG" ]; then
    echo "  Release: $RELEASE_TAG"
else
    echo "  Release: development (untagged)"
fi
echo ""

# ── Clone or checkout a sub-repo at the correct ref ──────────────────────────

_checkout_subrepo() {
    local name="$1"
    local url="$2"
    local dir="$3"

    if [ ! -d "$dir" ]; then
        if [ -n "$RELEASE_TAG" ]; then
            echo "Cloning $name @ $RELEASE_TAG..."
            if ! git clone --branch "$RELEASE_TAG" --depth 1 "$url" "$dir" 2>/dev/null; then
                echo ""
                echo "✗ ERROR: Release tag '$RELEASE_TAG' not found in $name."
                echo ""
                echo "  This means $name has not yet published a matching release."
                echo "  All three repos must be tagged together for a release to be installable."
                echo ""
                echo "  → https://github.com/Plasma-Deckery/$name/releases"
                echo ""
                exit 1
            fi
        else
            echo "Cloning $name (latest main)..."
            git clone "$url" "$dir"
        fi
    else
        if [ -n "$RELEASE_TAG" ]; then
            echo "$name: checking out $RELEASE_TAG..."
            git -C "$dir" fetch --tags --force
            if ! git -C "$dir" checkout -f "$RELEASE_TAG" 2>/dev/null; then
                echo ""
                echo "✗ ERROR: Release tag '$RELEASE_TAG' not found in $name."
                echo ""
                echo "  This means $name has not yet published a matching release."
                echo "  All three repos must be tagged together for a release to be installable."
                echo ""
                echo "  → https://github.com/Plasma-Deckery/$name/releases"
                echo ""
                exit 1
            fi
        else
            echo "$name: pulling latest..."
            git -C "$dir" pull --ff-only || echo "  (skipped — local changes present)"
        fi
    fi
}

# ── 1. Clone / update sub-repos ──────────────────────────────────────────────

echo "── Repositories ─────────────────────────────────────────────────────────"

_checkout_subrepo "makima-deckery" \
    "https://github.com/Plasma-Deckery/makima-deckery.git" \
    "$MAKIMA_DIR"

_checkout_subrepo "deckery-hud" \
    "https://github.com/Plasma-Deckery/deckery-hud.git" \
    "$HUD_DIR"

echo ""

# ── 2. Distrobox container ────────────────────────────────────────────────────
#
# Creates the container on first run; idempotent on subsequent runs.
# All sub-repos share this single container — package list lives here.

echo "── Container ────────────────────────────────────────────────────────────"
distrobox create --name deckery --image archlinux:latest || true
echo ""

# ── 3. Link default config ────────────────────────────────────────────────────
# Done before any service is started so makima always boots with a full config.

echo "── Config ───────────────────────────────────────────────────────────────"

# Migrate from the old ~/.config/makima/ path if needed.
_OLD_CFG="$HOME/.config/makima"
if [ -d "$_OLD_CFG" ] && [ ! -d "$CFG_DIR" ]; then
    mv "$_OLD_CFG" "$CFG_DIR"
    echo "Migrated: ~/.config/makima → ~/.config/deckery"
fi

mkdir -p "$CFG_DIR"

BASE_SRC="$DECKERY_DIR/configs/Steam Deck.toml"
BASE_DST="$CFG_DIR/Steam Deck.toml"
if [ -e "$BASE_DST" ] || [ -L "$BASE_DST" ]; then
    mv -f "$BASE_DST" "$BASE_DST.old"
    echo "Backed up: Steam Deck.toml → Steam Deck.toml.old"
fi
ln -sf "$BASE_SRC" "$BASE_DST"
echo "Linked: Steam Deck.toml"

for src in "$DECKERY_DIR/configs/Steam Deck::"*.toml; do
    [ -e "$src" ] || continue
    name="$(basename "$src")"
    dst="$CFG_DIR/$name"
    if [ -e "$dst" ]; then
        mv -f "$dst" "$dst.old"
        echo "Backed up: $name → $name.old"
    fi
    cp "$src" "$dst"
    echo "Installed: $name"
done

echo ""

# ── 4. Install Deckery Tray ───────────────────────────────────────────────────
#
# Tray is installed first because makima.service and deckery-hud.service both
# declare BindsTo=deckery-tray.service. The unit must exist before either
# service is started, otherwise systemd refuses to start them on reinstall.

echo "── Installing Deckery Tray ──────────────────────────────────────────────"
mkdir -p "$BIN_DIR"

TRAY_PACKAGES="python python-gobject python-cairo gtk3 libayatana-appindicator librsvg git"
distrobox enter deckery -- sudo pacman -S --needed --noconfirm $TRAY_PACKAGES
echo "Installed: tray packages"

TRAY_LAUNCH="$DECKERY_DIR/deckery-tray-launch"
chmod +x "$TRAY_LAUNCH"
ln -sf "$TRAY_LAUNCH" "$BIN_DIR/deckery-tray"
echo "Linked: $BIN_DIR/deckery-tray → $TRAY_LAUNCH"

mkdir -p "$SYSTEMD_DIR"
ln -sf "$DECKERY_DIR/systemd/deckery-tray.service" "$SYSTEMD_DIR/deckery-tray.service"
echo "Linked: deckery-tray.service"

systemctl --user daemon-reload
systemctl --user enable deckery-tray.service
systemctl --user restart deckery-tray.service \
    && echo "Service: deckery-tray restarted" \
    || echo "Service: could not restart deckery-tray (check: systemctl --user status deckery-tray)"
echo ""

# ── 5. Build and install Makima ───────────────────────────────────────────────

echo "── Building Makima ──────────────────────────────────────────────────────"
bash "$MAKIMA_DIR/install.sh"
echo ""

# ── 6. Install Deckery HUD ────────────────────────────────────────────────────

echo "── Installing Deckery HUD ───────────────────────────────────────────────"
bash "$HUD_DIR/install.sh"
echo ""

# ── 7. Legacy Steam Input config cleanup ─────────────────────────────────────
#
# Previous versions copied desktop_neptune.vdf to the config dir as a
# canonical reference for the tray watcher. This file is no longer needed.

echo "── Steam Input config ───────────────────────────────────────────────────"

_LEGACY_VDF="$CFG_DIR/desktop_neptune.vdf"
if [ -f "$_LEGACY_VDF" ]; then
    rm "$_LEGACY_VDF"
    echo "Removed legacy file: desktop_neptune.vdf"
else
    echo "OK: no legacy Steam config file found"
fi

echo ""

# ── 8. App icon + .desktop launcher ─────────────────────────────────────────

echo "── App launcher ─────────────────────────────────────────────────────────"

ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$ICON_DIR"
cp -f "$DECKERY_DIR/tray/icons/tray-ok.svg" "$ICON_DIR/deckery.svg"
echo "Installed: icon → $ICON_DIR/deckery.svg"

APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cp -f "$DECKERY_DIR/deckery.desktop" "$APPS_DIR/deckery.desktop"
echo "Installed: $APPS_DIR/deckery.desktop"

DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    cp -f "$DECKERY_DIR/deckery.desktop" "$DESKTOP_DIR/deckery.desktop"
    chmod +x "$DESKTOP_DIR/deckery.desktop"
    echo "Installed: ~/Desktop/deckery.desktop"
fi

gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo ""

# ── 9. Done ───────────────────────────────────────────────────────────────────

# ── Migration: remove legacy chattr +i lock if present ───────────────────────

_LEGACY_VDF="$HOME/.local/share/Steam/controller_base/desktop_neptune.vdf"
if lsattr "$_LEGACY_VDF" 2>/dev/null | awk '{print $1}' | grep -q 'i'; then
    echo "── Legacy lock detected ─────────────────────────────────────────────────"
    echo ""
    echo "  desktop_neptune.vdf is still locked with chattr +i from a previous"
    echo "  Deckery version. This is no longer needed — Steam Input is now"
    echo "  disabled via Steam's own config mechanism instead."
    echo ""
    if [ -t 0 ]; then
        read -p "  Remove the legacy lock now? [Y/n] " _ans
        _ans=${_ans:-Y}
        if [[ "$_ans" =~ ^[Yy]$ ]]; then
            if sudo chattr -i "$_LEGACY_VDF"; then
                echo "  ✓ Legacy lock removed."
            else
                echo "  ✗ Could not remove lock — run manually: sudo chattr -i $_LEGACY_VDF"
            fi
        fi
    else
        echo "  ⚠ Non-interactive install — remove manually: sudo chattr -i $_LEGACY_VDF"
    fi
    echo ""
fi

# ── Optional: disable Steam Input now ────────────────────────────────────────
#
# The tray will show a yellow indicator and let the user disable Steam Input
# at any time. Here we offer to do it immediately during install.

echo "── Steam Input ──────────────────────────────────────────────────────────"
echo ""
if distrobox enter deckery -- python3 "$DECKERY_DIR/tray/steam_bridge.py" --check 2>/dev/null; then
    echo "  OK: Steam Input already disabled — nothing to do."
else
    echo "  Deckery replaces Steam Input on the Desktop. You can disable Steam"
    echo "  Input now, or later via the tray icon (yellow indicator)."
    echo ""
    if [ -t 0 ]; then
        read -p "  Disable Steam Input now? [Y/n] " _steam_ans
        _steam_ans=${_steam_ans:-Y}
        if [[ "$_steam_ans" =~ ^[Yy]$ ]]; then
            if distrobox enter deckery -- python3 "$DECKERY_DIR/tray/steam_bridge.py"; then
                echo "  ✓ Steam Input disabled."
            else
                echo "  ✗ Could not apply — Steam may not be installed or never launched."
                echo "    You can apply it later via the tray icon."
            fi
        else
            echo "  Skipped. Apply later via the tray icon."
        fi
    else
        echo "  (non-interactive install — apply later via the tray icon)"
    fi
fi
echo ""

if [ "${DECKERY_ROLLBACK:-0}" = "1" ]; then
    echo "╔══════════════════════════════════════╗"
    echo "║           Update failed              ║"
    echo "╚══════════════════════════════════════╝"
    echo ""
    echo "  The update could not be installed due to an error."
    echo "  Deckery has been rolled back to ${DECKERY_RELEASE_TAG:-the previous version}."
    echo ""
else
    echo "╔══════════════════════════════════════╗"
    echo "║          Setup complete!             ║"
    echo "╚══════════════════════════════════════╝"
    echo ""
    echo "  Try it: press L3 (left stick click) — the HUD overlay should appear."
    echo ""
    echo "  Your config: $DECKERY_DIR/configs/Steam Deck.toml"
    echo "  Docs:        https://plasma-deckery.github.io/deckery/"
    echo ""
fi
