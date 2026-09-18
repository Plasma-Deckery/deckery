#!/bin/bash
# uninstall.sh — remove all Deckery services, binaries, and the distrobox container.
#
# What this removes:
#   - All Deckery systemd user services (stopped, disabled, deleted)
#   - Installed binaries and symlinks in ~/.local/bin/
#   - The deckery distrobox container
#   - Icon and .desktop launcher
#   - Config symlinks into the repo left by installs predating auto-discovery
#
# What this does NOT remove:
#   - Your own config files in ~/.config/deckery/
#   - Steam Input configset entry (413080 block removed from configset_controller_neptune.vdf)
#
# Pass --yes to skip the confirmation prompt.

set -e

BIN_DIR="$HOME/.local/bin"
SYSTEMD_DIR="$HOME/.config/systemd/user"
CFG_DIR="$HOME/.config/deckery"
SHARE_DIR="$HOME/.local/share/deckery"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
APPS_DIR="$HOME/.local/share/applications"

if [[ "$1" != "--yes" ]]; then
    echo ""
    echo "This will remove all Deckery services, binaries, the distrobox container,"
    echo "and the cloned repos in ~/.local/share/deckery/."
    echo "Your app configs in ~/.config/deckery/ will NOT be deleted."
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

# ── 7. Remove dangling config links ──────────────────────────────────────────
#
# Current installs put no links here — configs are read from the repo in place.
# An install predating that still has symlinks into the repo, and step 8 is
# about to delete what they point at, so they would be left dangling.
#
# Only links into $SHARE_DIR qualify. Every other symlink here is somebody's
# dotfile manager — chezmoi and friends install configs exactly this way — and
# deleting those would take real configuration with it while the line below
# promises the opposite.

echo "── Removing dangling config links ───────────────────────────────────────"
_removed=0
while IFS= read -r link; do
    target=$(readlink -f "$link" 2>/dev/null) || continue
    case "$target" in
        "$SHARE_DIR"/*) ;;
        *) continue ;;
    esac
    rm -f "$link" && echo "Removed: ${link#$CFG_DIR/}"
    _removed=1
done < <(find "$CFG_DIR" -type l -name "*.toml" 2>/dev/null)
[ "$_removed" -eq 0 ] && echo "Skipped: no links into $SHARE_DIR (your own config files are untouched)"
echo ""

# ── 8. Remove cloned repos ───────────────────────────────────────────────────
#
# ~/.local/share/deckery/ contains the cloned source repos and default configs.
# App-specific user configs live in ~/.config/deckery/ and are NOT removed.

echo "── Removing cloned repos ────────────────────────────────────────────────"
if [ -d "$SHARE_DIR" ]; then
    rm -rf "$SHARE_DIR" && echo "Removed: $SHARE_DIR"
else
    echo "Skipped: $SHARE_DIR not found"
fi
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────

echo "╔══════════════════════════════════════╗"
echo "║          Deckery uninstalled         ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  App configs kept in:"
echo "  ~/.config/deckery/"
echo ""
