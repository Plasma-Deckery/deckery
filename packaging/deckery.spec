Name:           deckery
Version:        0.3.0
Release:        1%{?dist}
Summary:        Steam Deck input stack for KDE Plasma — meta-package

# next_minor is the first version that would introduce a breaking change.
# Patch releases (0.3.x) are compatible and update independently.
# When a minor bump (0.4.0) happens: update Version, next_minor, and tag
# all component repos simultaneously.
%global next_minor 0.4

License:        GPL-3.0-only
URL:            https://github.com/Plasma-Deckery/deckery

Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

# Exact lower bound: components must be at least this release.
# Exact upper bound: components must be below the next breaking minor.
# This allows independent patch releases while preventing mixed-minor installs.
Requires:       makima-deckery >= %{version}
Requires:       makima-deckery <  %{next_minor}
Requires:       deckery-hud    >= %{version}
Requires:       deckery-hud    <  %{next_minor}
Requires:       deckery-tray   >= %{version}
Requires:       deckery-tray   <  %{next_minor}

%description
Deckery is a Steam Deck input stack for running KDE Plasma as a desktop
without Steam. This meta-package installs all components:

  makima-deckery  — evdev/hidraw input remapper (Rust, runs as user service)
  deckery-hud     — Wayland layer-shell button layout overlay (GTK4)
  deckery-tray    — System tray applet, game detector, onboarding (GTK3)

Install this package to get the full stack:
  dnf copr enable phischx/Deckery
  dnf install deckery

After install, enable and start the services:
  systemctl --user enable --now deckery-tray.service

%prep
%autosetup -n %{name}-%{version}

%build
# Nothing to build.

%install
# App icon (for .desktop and KDE launcher)
install -Dm644 tray/icons/tray-ok.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/deckery.svg

# Desktop launcher
install -Dm644 deckery.desktop \
    %{buildroot}%{_datadir}/applications/deckery.desktop

# Default configs — installed to system path; deckery-tray seeds
# ~/.config/deckery/ from here on first run.
install -dm755 %{buildroot}%{_datadir}/deckery/configs
install -pm644 "configs/Steam Deck.toml" \
    %{buildroot}%{_datadir}/deckery/configs/
for f in configs/Steam\ Deck::*.toml; do
    [ -f "$f" ] && install -pm644 "$f" %{buildroot}%{_datadir}/deckery/configs/
done
# VDF template for Steam Input onboarding (read via DECKERY_CONFIGS path)
install -pm644 configs/desktop_neptune.vdf \
    %{buildroot}%{_datadir}/deckery/configs/

%files
%license LICENSE
%doc README.md
%{_datadir}/icons/hicolor/scalable/apps/deckery.svg
%{_datadir}/applications/deckery.desktop
%{_datadir}/deckery/

%changelog
* Sat Aug 16 2026 Philipp Schimmelfennig <philipp@plasma-deckery.dev> - 0.3.0-1
- Initial meta-package release
- Pulls in makima-deckery, deckery-hud, deckery-tray at compatible versions
- Version range constraint: >= current minor, < next minor
  Patch releases update independently; minor bumps require coordinated release
