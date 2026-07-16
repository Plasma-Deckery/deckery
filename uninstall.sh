#!/bin/bash
# uninstall.sh — remove all Deckery services, binaries, and the distrobox container.
#
# What this removes:
#   - All Deckery systemd user services (stopped, disabled, deleted)
#   - Installed binaries and symlinks in ~/.local/bin/
#   - The deckery distrobox container
#   - Icon and .desktop launcher
#   - The Steam Deck.toml config symlink (not custom app configs or user edits)
#
# What this does NOT remove:
#   - The cloned repos in ~/.local/share/deckery/ (your configs live there)
#   - App-specific config files in ~/.config/makima/
#   - Steam Input configset entry (413080 block removed from configset_controller_neptune.vdf)
#
# Pass --yes to skip the confirmation prompt.

set -e

BIN_DIR="$HOME/.local/bin"
SYSTEMD_DIR="$HOME/.config/systemd/user"
CFG_DIR="$HOME/.config/makima"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
APPS_DIR="$HOME/.local/share/applications"

if [[ "$1" != "--yes" ]]; then
    echo ""
    echo "This will remove all Deckery services, binaries, and the distrobox container."
    echo "Your configs in ~/.local/share/deckery/ will NOT be deleted."
    echo ""
    read -r -p "Continue? [y/N] " reply
    [[ "$reply" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }
    echo ""
fi

# ── 1. Stop and disable services ─────────────────────────────────────────────

echo "── Stopping services ────────────────────────────────────────────────────"
for svc in makima.service makima-resume-watcher.service deckery-tray.service deckery-hud.service; do
    systemctl --user stop    "$svc" 2>/dev/null && echo "Stopped:  $svc" || true
    systemctl --user disable "$svc" 2>/dev/null && echo "Disabled: $svc" || true
done
echo ""

# ── 2. Remove service files ───────────────────────────────────────────────────

echo "── Removing service files ───────────────────────────────────────────────"
for svc in makima.service makima-resume-watcher.service deckery-tray.service deckery-hud.service; do
    rm -f "$SYSTEMD_DIR/$svc" && echo "Removed: $SYSTEMD_DIR/$svc" || true
done
systemctl --user daemon-reload
echo ""

# ── 3. Remove binaries and scripts ───────────────────────────────────────────

echo "── Removing binaries ────────────────────────────────────────────────────"
for bin in makima makima-deckery deckery-tray deckery-hud deckery-hud-toggle makima-resume-watcher; do
    rm -f "$BIN_DIR/$bin" && echo "Removed: $BIN_DIR/$bin" || true
done
echo ""

# ── 4. Restore Steam Input config ────────────────────────────────────────────

echo "── Restoring Steam Input config ─────────────────────────────────────────"
DECKERY_DIR="$(cd "$(dirname "$0")" && pwd)"
if python3 "$DECKERY_DIR/tray/steam_bridge.py" --remove 2>/dev/null; then
    echo "Removed: Steam Desktop controller config entry"
else
    echo "Skipped: Steam Input config not found or already removed"
fi
echo ""

# ── 5. Remove distrobox container ────────────────────────────────────────────

echo "── Removing distrobox container ─────────────────────────────────────────"
if distrobox list 2>/dev/null | grep -q "| deckery "; then
    distrobox rm deckery --force
    echo "Removed: deckery container"
else
    echo "Skipped: container 'deckery' not found"
fi
echo ""

# ── 6. Remove icon and desktop launcher ──────────────────────────────────────

echo "── Removing app launcher ────────────────────────────────────────────────"
rm -f "$ICON_DIR/deckery.svg"       && echo "Removed: deckery.svg" || true
rm -f "$APPS_DIR/deckery.desktop"   && echo "Removed: deckery.desktop" || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo ""

# ── 7. Remove config symlink ─────────────────────────────────────────────────

echo "── Removing config symlink ──────────────────────────────────────────────"
if [ -L "$CFG_DIR/Steam Deck.toml" ]; then
    rm "$CFG_DIR/Steam Deck.toml" && echo "Removed: Steam Deck.toml symlink"
else
    echo "Skipped: Steam Deck.toml (not a symlink — keeping user file)"
fi
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────

echo "╔══════════════════════════════════════╗"
echo "║          Deckery uninstalled         ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Repos and custom configs kept in:"
echo "  ~/.local/share/deckery/"
echo "  ~/.config/makima/"
echo ""
