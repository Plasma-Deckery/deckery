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
install -Dm644 packaging/deckery-tray-migrate.service \
    %{buildroot}%{_userunitdir}/deckery-tray-migrate.service

# Enabled for every user by the package (no manual `systemctl --user enable`):
# the tray starts with the graphical session and pulls in makima and the HUD.
install -dm755 %{buildroot}%{_userunitdir}/graphical-session.target.wants
ln -s ../deckery-tray.service \
    %{buildroot}%{_userunitdir}/graphical-session.target.wants/deckery-tray.service
install -dm755 %{buildroot}%{_userunitdir}/deckery-tray.service.wants
ln -s ../makima.service \
    %{buildroot}%{_userunitdir}/deckery-tray.service.wants/makima.service
ln -s ../deckery-hud.service \
    %{buildroot}%{_userunitdir}/deckery-tray.service.wants/deckery-hud.service

# Removes the plasma-core.target.wants link left by manual enables under
# <= 0.4.0, which forms an ordering cycle with the current unit.
install -dm755 %{buildroot}%{_userunitdir}/default.target.wants
ln -s ../deckery-tray-migrate.service \
    %{buildroot}%{_userunitdir}/default.target.wants/deckery-tray-migrate.service
ln -s ../deckery-tray-migrate.service \
    %{buildroot}%{_userunitdir}/graphical-session.target.wants/deckery-tray-migrate.service

%post
%systemd_user_post deckery-tray.service

%preun
%systemd_user_preun deckery-tray.service

%files
%license LICENSE
%doc README.md
%{_prefix}/lib/deckery/tray/
%{_userunitdir}/deckery-tray.service
%{_userunitdir}/deckery-tray-migrate.service
%dir %{_userunitdir}/deckery-tray.service.wants
%{_userunitdir}/deckery-tray.service.wants/makima.service
%{_userunitdir}/deckery-tray.service.wants/deckery-hud.service
%{_userunitdir}/graphical-session.target.wants/deckery-tray.service
%{_userunitdir}/graphical-session.target.wants/deckery-tray-migrate.service
%{_userunitdir}/default.target.wants/deckery-tray-migrate.service

%changelog
* Tue Nov 10 2026 Philipp Schimmelfennig <philipp@plasma-deckery.dev> - 0.5.0-0
- Enabled for every user by the package: the tray starts with the graphical
  session and pulls in makima and the HUD; no manual systemctl --user enable
- New deckery-tray-migrate.service removes the plasma-core.target.wants link
  left by manual enables under <= 0.4.0, which formed an ordering cycle and
  kept the whole stack from starting (Issue #77)

* Mon Sep 15 2026 Philipp Schimmelfennig <philipp@plasma-deckery.dev> - 0.4.1-0
- Beta builds for 0.4.1 cycle (built from main)
