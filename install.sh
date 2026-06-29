#!/bin/bash
# install.sh — Deckery full-stack installer.
#
# Clones all required repos, sets up the distrobox container,
# builds and installs all services. Re-running is safe (idempotent).
#
# Usage (first install):
#   git clone https://github.com/Plasma-Deckery/deckery.git ~/Programming/deckery
#   bash ~/Programming/deckery/install.sh
#
# Usage (update):
#   cd ~/Programming/deckery && git pull && bash install.sh

set -e

DECKERY_DIR="$(dirname "$(readlink -f "$0")")"
PARENT_DIR="$(dirname "$DECKERY_DIR")"
MAKIMA_DIR="$PARENT_DIR/makima-deckery"
HUD_DIR="$PARENT_DIR/deckery-hud"
BIN_DIR="$HOME/.local/bin"
CFG_DIR="$HOME/.config/makima"
SYSTEMD_DIR="$HOME/.config/systemd/user"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║         Deckery Installer            ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. Clone / update sub-repos ──────────────────────────────────────────────

echo "── Repositories ─────────────────────────────────────────────────────────"

if [ ! -d "$MAKIMA_DIR" ]; then
    echo "Cloning makima-deckery..."
    git clone https://github.com/Plasma-Deckery/makima-deckery.git "$MAKIMA_DIR"
else
    echo "makima-deckery: pulling latest..."
    git -C "$MAKIMA_DIR" pull --ff-only || echo "  (skipped — local changes present)"
fi

if [ ! -d "$HUD_DIR" ]; then
    echo "Cloning deckery-hud..."
    git clone https://github.com/Plasma-Deckery/deckery-hud.git "$HUD_DIR"
else
    echo "deckery-hud: pulling latest..."
    git -C "$HUD_DIR" pull --ff-only || echo "  (skipped — local changes present)"
fi

echo ""

# ── 2. Distrobox container ────────────────────────────────────────────────────
#
# Creates the container on first run; idempotent on subsequent runs.
# All sub-repos share this single container — package list lives here.

echo "── Container ────────────────────────────────────────────────────────────"
distrobox assemble create --file "$DECKERY_DIR/distrobox.ini"
echo ""

# ── 3. Build and install Makima ───────────────────────────────────────────────

echo "── Building Makima ──────────────────────────────────────────────────────"
bash "$MAKIMA_DIR/install.sh"
echo ""

# ── 4. Install Deckery HUD ────────────────────────────────────────────────────

echo "── Installing Deckery HUD ───────────────────────────────────────────────"
bash "$HUD_DIR/install.sh"
echo ""

# ── 5. Install Deckery Tray ───────────────────────────────────────────────────

echo "── Installing Deckery Tray ──────────────────────────────────────────────"
mkdir -p "$BIN_DIR"

TRAY_PACKAGES="python python-gobject gtk3 libayatana-appindicator librsvg"
distrobox enter deckery -- sudo pacman -S --needed --noconfirm $TRAY_PACKAGES
echo "Installed: tray packages"

TRAY_LAUNCH="$DECKERY_DIR/deckery-tray-launch"
chmod +x "$TRAY_LAUNCH"
ln -sf "$TRAY_LAUNCH" "$BIN_DIR/deckery-tray"
echo "Linked: $BIN_DIR/deckery-tray → $TRAY_LAUNCH"

mkdir -p "$SYSTEMD_DIR"
ln -sf "$DECKERY_DIR/systemd/deckery-tray.service" "$SYSTEMD_DIR/deckery-tray.service"
echo "Linked: deckery-tray.service"

DROPIN_DIR="$SYSTEMD_DIR/makima.service.d"
mkdir -p "$DROPIN_DIR"
cat > "$DROPIN_DIR/deckery.conf" <<'EOF'
[Unit]
PartOf=deckery-tray.service
After=deckery-tray.service
EOF
echo "Installed: makima drop-in (PartOf deckery-tray)"

systemctl --user daemon-reload
systemctl --user enable --now deckery-tray.service \
    && echo "Service: deckery-tray started" \
    || echo "Service: could not start deckery-tray (check: systemctl --user status deckery-tray)"
echo ""

# ── 6. Steam Input config (desktop_neptune.vdf) ──────────────────────────────
#
# Copies the Deckery-tuned desktop controller config into Steam's config dir.
# Idempotent: skipped if the destination is already identical to the source.
# Note: locking with chattr +i is a separate manual step until the file-watcher
# solution is in place (see deckery#11).

echo "── Steam Input config ───────────────────────────────────────────────────"

VDF_SRC="$DECKERY_DIR/docs/desktop_neptune.vdf"
VDF_DST="$HOME/.local/share/Steam/controller_base/desktop_neptune.vdf"

if [ -f "$VDF_SRC" ]; then
    if ! cmp -s "$VDF_SRC" "$VDF_DST" 2>/dev/null; then
        cp "$VDF_SRC" "$VDF_DST"
        echo "Installed: desktop_neptune.vdf"
    else
        echo "Already up to date: desktop_neptune.vdf"
    fi
else
    echo "Skipped: desktop_neptune.vdf not found in repo"
fi

echo ""

# ── 8. App icon + .desktop launcher ──────────────────────────────────────────

echo "── App launcher ─────────────────────────────────────────────────────────"

ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$ICON_DIR"
cp -f "$DECKERY_DIR/tray/icons/tray-ok.svg" "$ICON_DIR/deckery.svg"
echo "Installed: icon → $ICON_DIR/deckery.svg"

APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
cp -f "$DECKERY_DIR/deckery.desktop" "$APPS_DIR/deckery.desktop"
echo "Installed: $APPS_DIR/deckery.desktop"

gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo ""

# ── 9. Link default config ────────────────────────────────────────────────────

echo "── Config ───────────────────────────────────────────────────────────────"
mkdir -p "$CFG_DIR"

BASE_SRC="$DECKERY_DIR/configs/Steam Deck.toml"
BASE_DST="$CFG_DIR/Steam Deck.toml"
if [ ! -e "$BASE_DST" ]; then
    ln -sf "$BASE_SRC" "$BASE_DST"
    echo "Linked: Steam Deck.toml"
elif [ -L "$BASE_DST" ]; then
    echo "Already linked: Steam Deck.toml"
else
    echo "Skipped: Steam Deck.toml (already exists as regular file — not overwriting)"
fi

for src in "$DECKERY_DIR/configs/Steam Deck::"*.toml; do
    [ -e "$src" ] || continue
    name="$(basename "$src")"
    dst="$CFG_DIR/$name"
    if [ ! -e "$dst" ]; then
        cp "$src" "$dst"
        echo "Installed: $name"
    else
        echo "Already present: $name (not overwriting)"
    fi
done

echo ""

# ── 10. Done ──────────────────────────────────────────────────────────────────

echo "╔══════════════════════════════════════╗"
echo "║          Setup complete!             ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Try it: hold L1 on your Steam Deck — the HUD overlay should appear."
echo ""
echo "  Your config: $DECKERY_DIR/configs/Steam Deck.toml"
echo "  Docs:        https://github.com/Plasma-Deckery/deckery/wiki"
echo ""
