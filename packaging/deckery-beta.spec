Name:           deckery
Version:        %{git_version}
Release:        %{beta_release}%{?dist}
Summary:        Steam Deck input stack for KDE Plasma — meta-package (beta)

# Beta channel: Version and Release are injected by .copr/Makefile at build time.
# Version = last stable git tag; Release = 0.YYYYMMDD.gHASH
# Stable release (Release: 1) always wins over beta (Release: 0.*).
%global next_minor 0.5

License:        GPL-3.0-only
URL:            https://github.com/Plasma-Deckery/deckery

Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildArch:      noarch

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

This is the BETA channel package — built from main on every commit.

%prep
%autosetup -n %{name}-%{version}

%build
# Nothing to build.

%install
install -Dm644 tray/icons/tray-ok.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/deckery.svg

install -Dm644 deckery.desktop \
    %{buildroot}%{_datadir}/applications/deckery.desktop

install -dm755 %{buildroot}%{_datadir}/deckery/configs/apps
find configs -name "*.toml" | while read f; do
    rel="${f#configs/}"
    install -Dpm644 "$f" "%{buildroot}%{_datadir}/deckery/configs/$rel"
done

%files
%license LICENSE
%doc README.md
%{_datadir}/icons/hicolor/scalable/apps/deckery.svg
%{_datadir}/applications/deckery.desktop
%{_datadir}/deckery/

%changelog
* Mon Sep 15 2026 Philipp Schimmelfennig <philipp@plasma-deckery.dev> - 0.4.1-0
- Beta builds for 0.4.1 cycle (built from main)
