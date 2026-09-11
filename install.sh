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

if ! command -v distrobox &>/dev/null; then
    echo ""
    echo "✗ distrobox is not installed."
    echo ""
    echo "  Deckery requires distrobox to build and run its services."
    echo "  Please install it using your distribution's package manager,"
    echo "  then re-run the installer."
    echo ""
    echo "  → https://distrobox.it/#installation"
    echo ""
    exit 1
fi

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
#
# Two invariants govern everything below, and both used to be violated.
#
# 1. remote.origin.fetch must stay the standard branch refspec. Cloning with
#    --branch <tag> sets it to that one tag instead, and a repo in that state
#    can never see origin/main again — no tracking, no pull, pinned to the
#    release it was installed at, silently and permanently. So we clone plain
#    and check the tag out afterwards, and we rewrite the refspec on every run
#    so installs already broken in the field repair themselves.
#
# 2. The checkout is somebody's working directory. makima and the HUD get
#    edited in place when testing on a device or in a VM, so nothing on the
#    main path may reset, force or discard. Where we cannot fast-forward we
#    say why and move on.

_missing_tag_error() {
    echo ""
    echo "✗ ERROR: Release tag '$RELEASE_TAG' not found in $1."
    echo ""
    echo "  This means $1 has not yet published a matching release."
    echo "  All three repos must be tagged together for a release to be installable."
    echo ""
    echo "  → https://github.com/Plasma-Deckery/$1/releases"
    echo ""
    exit 1
}

# Idempotent; also repairs clones made by older installers with --branch <tag>.
_repair_refspec() {
    git -C "$1" config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
}

# Fast-forward an existing checkout to origin/main, or explain why we won't.
_update_to_main() {
    local name="$1" dir="$2" branch head target

    branch="$(git -C "$dir" symbolic-ref --quiet --short HEAD || true)"

    if [ -z "$branch" ]; then
        # Detached — typically left behind by an earlier release install.
        echo "$name: detached HEAD → switching to main"
        git -C "$dir" checkout main 2>/dev/null \
            || git -C "$dir" checkout -b main --track origin/main
        branch=main
    fi

    if [ "$branch" != "main" ]; then
        echo "  ⚠ $name: on branch '$branch', not main — left untouched"
        return
    fi

    # Without this a plain `git pull` fails with "no tracking information",
    # which the old code reported as "local changes present".
    git -C "$dir" branch --set-upstream-to=origin/main main >/dev/null 2>&1 || true

    head="$(git -C "$dir" rev-parse HEAD)"
    target="$(git -C "$dir" rev-parse origin/main)"

    if [ "$head" = "$target" ]; then
        echo "$name: already up to date"
    elif ! git -C "$dir" merge-base --is-ancestor HEAD origin/main; then
        echo "  ⚠ $name: has local commits not on origin/main — left untouched"
    elif ! git -C "$dir" merge --ff-only origin/main >/dev/null 2>&1; then
        # Git's own message ends in "Aborting", which reads like the installer
        # gave up. Name the files in the way instead — that is the actionable part.
        echo "  ⚠ $name: fast-forward blocked by uncommitted changes — left untouched"
        git -C "$dir" diff --name-only | sed 's/^/      /'
    fi
}

_checkout_subrepo() {
    local name="$1"
    local url="$2"
    local dir="$3"

    if [ ! -d "$dir" ]; then
        echo "Cloning $name..."
        # --filter=blob:none keeps the clone fast without truncating refs the
        # way --depth 1 does.
        git clone --filter=blob:none "$url" "$dir"
        _repair_refspec "$dir"
    else
        _repair_refspec "$dir"
        echo "$name: fetching..."
        git -C "$dir" fetch origin --tags --force
    fi

    if [ -n "$RELEASE_TAG" ]; then
        echo "$name: checking out $RELEASE_TAG..."
        # --force is deliberate here: a release install means "give me exactly
        # this tag". The non-destructive handling applies to the main path.
        git -C "$dir" checkout --force "$RELEASE_TAG" 2>/dev/null \
            || _missing_tag_error "$name"
    else
        _update_to_main "$name" "$dir"
    fi
}

# One line per repo: branch, what it tracks, where it stands. Drift of the kind
# fixed above is invisible until somebody looks, so the installer looks.
_repo_summary() {
    local name="$1" dir="$2" branch tracking
    # `return 0`, not a bare `return`: a bare one passes the failed test's
    # status up, and under `set -e` that aborts the installer — in the one
    # function whose entire job is to report rather than act.
    [ -d "$dir/.git" ] || return 0
    branch="$(git -C "$dir" symbolic-ref --quiet --short HEAD \
        || echo "detached@$(git -C "$dir" describe --tags --always HEAD 2>/dev/null)")"
    tracking="$(git -C "$dir" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || echo '—')"
    printf '  %-16s %-24s → %-14s %s\n' \
        "$name" "$branch" "$tracking" "$(git -C "$dir" log --oneline -1 --format='%h %s' | cut -c1-46)"
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
_repo_summary "deckery"        "$DECKERY_DIR"
_repo_summary "makima-deckery" "$MAKIMA_DIR"
_repo_summary "deckery-hud"    "$HUD_DIR"

echo ""

# ── 2. Distrobox container ────────────────────────────────────────────────────
#
# Creates the container on first run; idempotent on subsequent runs.
# All sub-repos share this single container — package list lives here.

echo "── Container ────────────────────────────────────────────────────────────"
if ! distrobox list 2>/dev/null | grep -q "| deckery "; then
    distrobox create --name deckery --image archlinux:latest --yes
fi
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

# Install all non-base configs recursively (modules, app overrides, subdirs).
# Skips Steam Deck.toml (already linked above) and the base config itself.
while IFS= read -r src; do
    rel="${src#$DECKERY_DIR/configs/}"
    [ "$rel" = "Steam Deck.toml" ] && continue
    dst="$CFG_DIR/$rel"
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ]; then
        mv -f "$dst" "$dst.old"
        echo "Backed up: $rel → $rel.old"
    fi
    cp "$src" "$dst"
    echo "Installed: $rel"
done < <(find "$DECKERY_DIR/configs" -name "*.toml" | sort)

echo ""

# ── 4. Install Deckery Tray ───────────────────────────────────────────────────
#
# Tray is installed first because makima.service and deckery-hud.service both
# declare BindsTo=deckery-tray.service. The unit must exist before either
# service is started, otherwise systemd refuses to start them on reinstall.

echo "── Installing Deckery Tray ──────────────────────────────────────────────"
mkdir -p "$BIN_DIR"

TRAY_PACKAGES="python python-gobject python-cairo gtk3 libayatana-appindicator librsvg git"
_TRAY_STAMP="/var/cache/deckery-tray-packages.stamp"
_TRAY_HASH="$(echo "$TRAY_PACKAGES" | md5sum | cut -d' ' -f1)"
if [ "$(distrobox enter deckery -- cat "$_TRAY_STAMP" 2>/dev/null)" != "$_TRAY_HASH" ]; then
    distrobox enter deckery -- sudo pacman -S --needed --noconfirm $TRAY_PACKAGES
    echo "$_TRAY_HASH" | distrobox enter deckery -- sudo tee "$_TRAY_STAMP" > /dev/null
fi
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
