# package-guard.sh — refuse a source install on top of a packaged Deckery.
#
# Sourced by install.sh, and by get.sh straight out of the fetched repo.
# Defines deckery_package_guard; running it has no side effects.
#
# A source install next to the RPMs (layered via rpm-ostree on Bazzite/Fedora
# Atomic, or dnf on Fedora) is a second, complete installation: its user units
# and binaries in ~/.local shadow the packaged ones, and the package's updates
# silently stop having any effect. Developers who want exactly that set
# DECKERY_FORCE_SOURCE=1 (get.sh: --force-source).

DECKERY_PACKAGES="deckery deckery-tray makima-deckery deckery-hud"

# Commands run on the host, also when the installer runs inside a container
# (an rpm in there would query the container's own, empty database).
_deckery_on_host() {
    if [ -e /run/.containerenv ] || [ -e /.dockerenv ]; then
        command -v distrobox-host-exec >/dev/null 2>&1 || return 127
        distrobox-host-exec "$@"
    else
        "$@"
    fi
}

# Prints the installed Deckery packages, one "name version" per line.
_deckery_installed_packages() {
    local out
    # shellcheck disable=SC2086
    out="$(_deckery_on_host rpm -q --qf '%{NAME} %{VERSION}-%{RELEASE}\n' \
        $DECKERY_PACKAGES 2>/dev/null | grep -v 'is not installed')"
    if [ -n "$out" ]; then
        printf '%s\n' "$out"
        return 0
    fi
    # Layered but not booted yet (staged deployment), or no usable rpm: ask
    # rpm-ostree which packages any deployment requests or has layered.
    out="$(_deckery_on_host rpm-ostree status --json 2>/dev/null \
        | grep -Eo "\"($(echo $DECKERY_PACKAGES | tr ' ' '|'))\"" \
        | tr -d '"' | sort -u)"
    [ -n "$out" ] || return 1
    printf '%s (layered, version unknown)\n' $out
}

deckery_package_guard() {
    [ "${DECKERY_FORCE_SOURCE:-0}" = "1" ] && return 0

    local pkgs names atomic=0
    pkgs="$(_deckery_installed_packages)" || return 0
    names="$(printf '%s\n' "$pkgs" | awk '{print $1}' | tr '\n' ' ')"
    _deckery_on_host test -e /run/ostree-booted 2>/dev/null && atomic=1

    echo ""
    echo "✗ Deckery is installed as a system package:"
    printf '%s\n' "$pkgs" | sed 's/^/    /'
    echo ""
    if [ "$atomic" = "1" ]; then
        echo "  Update it via your system update (rpm-ostree upgrade)."
    else
        echo "  Update it via your system update (sudo dnf upgrade)."
    fi
    echo "  A source install would add a second installation that shadows the package."
    echo ""
    echo "  To switch to a source install, remove the package first:"
    if [ "$atomic" = "1" ]; then
        echo "    rpm-ostree uninstall ${names% }   (then reboot)"
    else
        echo "    sudo dnf remove ${names% }"
    fi
    echo ""
    echo "  Developers who want both anyway: DECKERY_FORCE_SOURCE=1, or get.sh --force-source"
    echo ""
    return 1
}
