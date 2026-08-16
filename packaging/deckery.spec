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
# Nothing to prepare — meta-package only.

%build
# Nothing to build.

%install
# Nothing to install — all files ship in the component packages.

%files
%license LICENSE
%doc README.md

%changelog
* Sat Aug 16 2026 Philipp Schimmelfennig <philipp@plasma-deckery.dev> - 0.3.0-1
- Initial meta-package release
- Pulls in makima-deckery, deckery-hud, deckery-tray at compatible versions
- Version range constraint: >= current minor, < next minor
  Patch releases update independently; minor bumps require coordinated release
