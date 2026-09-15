Name:           deckery-tray
Version:        %{git_version}
Release:        %{beta_release}%{?dist}
Summary:        Deckery system tray — service monitor and control for KDE Plasma (beta)

# Beta channel: Version and Release are injected by .copr/Makefile at build time.
# Version = last stable git tag; Release = 0.YYYYMMDD.gHASH
# Stable release (Release: 1) always wins over beta (Release: 0.*).

License:        GPL-3.0-only
URL:            https://github.com/Plasma-Deckery/deckery

Source0:        %{url}/archive/v%{version}/deckery-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       python3-gobject
Requires:       gtk3
Requires:       libayatana-appindicator-gtk3
Requires:       libnotify
Requires:       python3-psutil
Requires:       glib2

Requires:       makima-deckery >= %{version}
Requires:       deckery-hud >= %{version}

%description
deckery-tray is a GTK3 system tray applet that monitors and controls the
Deckery input stack. This is the BETA channel package — built from main
on every commit.

%prep
%autosetup -n deckery-%{version}

%build
# Pure Python — nothing to compile.

%install
install -dm755 %{buildroot}%{_prefix}/lib/deckery/tray
install -pm644 tray/*.py %{buildroot}%{_prefix}/lib/deckery/tray/

install -dm755 %{buildroot}%{_prefix}/lib/deckery/tray/setup
install -pm644 tray/setup/*.py %{buildroot}%{_prefix}/lib/deckery/tray/setup/

install -dm755 %{buildroot}%{_prefix}/lib/deckery/tray/icons
install -pm644 tray/icons/*.svg %{buildroot}%{_prefix}/lib/deckery/tray/icons/

install -Dm644 packaging/deckery-tray.service \
    %{buildroot}%{_userunitdir}/deckery-tray.service

%post
%systemd_user_post deckery-tray.service

%preun
%systemd_user_preun deckery-tray.service

%files
%license LICENSE
%doc README.md
%{_prefix}/lib/deckery/tray/
%{_userunitdir}/deckery-tray.service

%changelog
* Mon Sep 15 2026 Philipp Schimmelfennig <philipp@plasma-deckery.dev> - 0.4.1-0
- Beta builds for 0.4.1 cycle (built from main)
